from datetime import date, datetime, timedelta, timezone

import config
from db import db
from models.app_users import AppUser
from models.calendar_events import CalendarEvent
from models.sprints import Sprint
from models.task_statuses import TaskStatus
from models.tasks import Task
from util.access_control import can_access_company
from util.company_workflow import company_by_id, done_status_names
from util.task_sprint import add_task_to_sprint, remove_task_from_sprint
from util.task_workload import week_bounds


def _sync_config(company):
    if not company:
        return None
    return config.company_calendar_task_sync.get(company.name)


def uses_weekly_sprints(company_id):
    company = company_by_id(company_id)
    sync_cfg = _sync_config(company)
    return bool(sync_cfg and sync_cfg.get("sprint_duration_days") == 7)


def my_tasks_current_week_only(company_id):
    company = company_by_id(company_id)
    sync_cfg = _sync_config(company)
    return bool(sync_cfg and sync_cfg.get("my_tasks_current_week_only"))


def _task_sprint_date(task):
    """Shoot day for calendar tasks; due date for everything else."""
    if task.calendar_event_id:
        event = (
            db.session.query(CalendarEvent)
            .filter(CalendarEvent.calendar_event_id == task.calendar_event_id)
            .first()
        )
        if event and event.event_date:
            return event.event_date
    return task.due_date


def _week_sprint_name(week_start, week_end):
    if week_start.month == week_end.month:
        return f"{week_start.strftime('%b %d')} – {week_end.strftime('%d, %Y')}"
    return f"{week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"


def _resolve_actor_id(company_id, created_by_id=None):
    if created_by_id:
        return created_by_id

    existing = (
        db.session.query(Sprint.created_by_id)
        .filter(Sprint.company_id == company_id)
        .order_by(Sprint.created_at.desc())
        .first()
    )
    if existing:
        return existing[0]

    users = db.session.query(AppUser).filter(AppUser.active.is_(True)).all()
    for user in users:
        if can_access_company(user, company_id):
            return user.user_id
    return None


def _find_week_sprint(company_id, week_start, active_only=True):
    query = db.session.query(Sprint).filter(Sprint.company_id == company_id)
    if active_only:
        query = query.filter(Sprint.active.is_(True))

    for sprint in query.all():
        if sprint.start_date and sprint.start_date.date() == week_start:
            return sprint
    return None


def _find_or_create_week_sprint(company_id, week_start, created_by_id):
    week_end = week_start + timedelta(days=6)
    sprint = _find_week_sprint(company_id, week_start)
    if sprint:
        return sprint

    actor_id = _resolve_actor_id(company_id, created_by_id)
    if not actor_id:
        return None

    start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(week_end, datetime.max.time()).replace(tzinfo=timezone.utc)
    sprint = Sprint(
        company_id=company_id,
        name=_week_sprint_name(week_start, week_end),
        created_by_id=actor_id,
        start_date=start_dt,
        end_date=end_dt,
    )
    db.session.add(sprint)
    db.session.flush()
    return sprint


def _task_is_done(task, company_id):
    done_names = set(done_status_names(company_id))
    status = task.status
    if status and status.name in done_names:
        return True

    status_row = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.task_status_id == task.task_status_id)
        .first()
    )
    return bool(status_row and status_row.name in done_names)


def _rollover_sprint_tasks(old_sprint, current_sprint, company_id):
    moved = 0
    for task in list(old_sprint.tasks):
        if not task.active:
            remove_task_from_sprint(old_sprint, task)
            continue
        if _task_is_done(task, company_id):
            remove_task_from_sprint(old_sprint, task)
            continue
        if task not in current_sprint.tasks:
            add_task_to_sprint(current_sprint, task)
            moved += 1
        remove_task_from_sprint(old_sprint, task)
    return moved


def ensure_weekly_sprint_rollover(company_id, created_by_id=None):
    """
    Ensure the current Mon–Sun sprint exists, roll incomplete tasks forward from
    older sprints, and archive prior weeks.
    """
    if not uses_weekly_sprints(company_id):
        return None

    week_start, week_end = week_bounds()
    current_sprint = _find_or_create_week_sprint(company_id, week_start, created_by_id)
    if not current_sprint:
        return None

    changed = False
    old_sprints = (
        db.session.query(Sprint)
        .filter(Sprint.company_id == company_id)
        .filter(Sprint.active.is_(True))
        .filter(Sprint.sprint_id != current_sprint.sprint_id)
        .all()
    )

    for old_sprint in old_sprints:
        if _rollover_sprint_tasks(old_sprint, current_sprint, company_id):
            changed = True
        old_sprint.active = False
        old_sprint.tasks.clear()
        changed = True

    if changed:
        db.session.commit()

    return current_sprint


def sync_due_tasks_into_current_week_sprint(company_id, created_by_id=None):
    """Add active tasks due this week (or earlier) to the current weekly sprint."""
    if not uses_weekly_sprints(company_id):
        return 0

    current_sprint = ensure_weekly_sprint_rollover(company_id, created_by_id)
    if not current_sprint:
        return 0

    week_start, week_end = week_bounds()
    tasks = (
        db.session.query(Task)
        .filter(Task.company_id == company_id)
        .filter(Task.active.is_(True))
        .all()
    )

    promoted = 0
    for task in tasks:
        sprint_date = _task_sprint_date(task)
        if not sprint_date or sprint_date < week_start or sprint_date > week_end:
            continue
        if task in current_sprint.tasks:
            continue
        for sprint in list(task.sprints):
            remove_task_from_sprint(sprint, task)
        add_task_to_sprint(current_sprint, task)
        promoted += 1

    if promoted:
        db.session.commit()
    return promoted


def sync_task_weekly_sprint_membership(task, created_by_id=None):
    """Keep a task in the current weekly sprint when due this week, otherwise backlog."""
    sync_cfg = _sync_config(company_by_id(task.company_id))
    if not sync_cfg or not sync_cfg.get("backlog_until_picture_day"):
        return

    if not uses_weekly_sprints(task.company_id):
        return

    sprint_date = _task_sprint_date(task)
    if not sprint_date:
        return

    week_start, week_end = week_bounds()
    current_sprint = ensure_weekly_sprint_rollover(task.company_id, created_by_id or task.created_by_id)
    if not current_sprint:
        return

    if sprint_date > week_end:
        task.sprints.clear()
        status_name = sync_cfg.get("task_status", config.SCHOOL_PICTURE_STAGE_PICTURES)
        backlog_status = (
            db.session.query(TaskStatus)
            .filter(TaskStatus.company_id == task.company_id)
            .filter(TaskStatus.name == status_name)
            .first()
        )
        if backlog_status:
            task.task_status_id = backlog_status.task_status_id
        return

    for sprint in list(task.sprints):
        if sprint.sprint_id != current_sprint.sprint_id:
            remove_task_from_sprint(sprint, task)
    if task not in current_sprint.tasks:
        add_task_to_sprint(current_sprint, task)
