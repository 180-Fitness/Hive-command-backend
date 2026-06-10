from datetime import date

from random import choice

import config
from sqlalchemy import func

from db import db
from models.app_users import AppUser
from models.calendar_events import PICTURE_DAY_TYPES, CalendarEvent
from models.companies import Company
from models.projects import Project
from models.task_statuses import TaskStatus
from models.tasks import Task
from util.access_control import can_access_company
from util.company_workflow import company_by_id
from util.school_picture_workflow import sync_school_picture_assignee
from util.weekly_sprints import (
    my_tasks_current_week_only,
    sync_due_tasks_into_current_week_sprint,
    sync_task_weekly_sprint_membership,
)


def _sync_config(company):
    if not company:
        return None
    return config.company_calendar_task_sync.get(company.name)


def is_shoot_event(event, sync_cfg):
    event_type = (event.event_type or "").strip()
    if event_type in sync_cfg.get("shoot_event_types", list(PICTURE_DAY_TYPES)):
        return True
    keyword = (sync_cfg.get("shoot_keyword") or "").strip().lower()
    if not keyword:
        return False
    haystacks = (event_type, event.title or "", event.school or "")
    return any(keyword in value.lower() for value in haystacks if value)


def _normalized_name(value):
    return (value or "").strip().casefold()


def _find_assignee(company_id, assignee_cfg):
    first = _normalized_name(assignee_cfg.get("first_name"))
    last = _normalized_name(assignee_cfg.get("last_name"))
    if not first or not last:
        return None

    candidates = (
        db.session.query(AppUser)
        .filter(AppUser.active.is_(True))
        .filter(func.lower(AppUser.first_name) == first)
        .filter(func.lower(AppUser.last_name) == last)
        .all()
    )
    for user in candidates:
        if can_access_company(user, company_id):
            return user
    return None


def _find_or_create_project(company, school, created_by_id):
    school = (school or "").strip()
    if not school:
        return None

    target = _normalized_name(school)
    projects = (
        db.session.query(Project)
        .filter(Project.company_id == company.company_id)
        .filter(Project.active.is_(True))
        .all()
    )
    for project in projects:
        if _normalized_name(project.name) != target:
            continue
        if project.user_deleted:
            return None
        return project

    project = Project(
        company_id=company.company_id,
        name=school,
        created_by_id=created_by_id,
        color=company.color or choice(config.palette),
        description="",
    )
    db.session.add(project)
    db.session.flush()
    return project


def _default_task_status(company_id, status_name):
    return (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .filter(TaskStatus.name == status_name)
        .first()
    )


def task_shoot_date(task):
    if not task.calendar_event_id:
        return None
    event = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.calendar_event_id == task.calendar_event_id)
        .first()
    )
    return event.event_date if event else None


def task_sprint_date(task):
    """Date that drives sprint/backlog timing (shoot day for calendar tasks)."""
    return task_shoot_date(task) or task.due_date


def _task_description(event):
    parts = []
    if event.event_date:
        parts.append(f"Picture day: {event.event_date.strftime('%B %d, %Y')}")
    if event.event_type:
        parts.append(f"Event type: {event.event_type}")
    if event.location:
        parts.append(f"Location: {event.location}")
    if event.num_students is not None:
        parts.append(f"Students: {event.num_students}")
    if event.num_stations is not None:
        parts.append(f"Stations: {event.num_stations}")
    if event.description:
        parts.append(event.description)
    return "\n".join(parts)


def _task_name(event):
    return (event.title or "").strip() or (event.school or "").strip() or "Shoot"


def my_tasks_require_sprint(company_id):
    """Deprecated: use my_tasks_current_week_only from util.weekly_sprints."""
    return my_tasks_current_week_only(company_id)


def _sync_sprint_membership(task, created_by_id=None):
    sync_task_weekly_sprint_membership(task, created_by_id)


def promote_due_calendar_shoots_to_sprint(company_id, created_by_id=None):
    """Move due shoots into the current weekly sprint."""
    return sync_due_tasks_into_current_week_sprint(company_id, created_by_id)


def _resolve_project(company, event, created_by_id):
    if event.project_id:
        project = (
            db.session.query(Project)
            .filter(Project.project_id == event.project_id)
            .filter(Project.company_id == company.company_id)
            .filter(Project.active.is_(True))
            .first()
        )
        if project:
            return project

    school = (event.school or "").strip()
    if not school:
        return None
    return _find_or_create_project(company, school, created_by_id)


def sync_calendar_event_to_task(event, created_by_id=None):
    """Create or update a White Raven task for a calendar shoot event."""
    if not event or not event.active:
        return None

    company = company_by_id(event.company_id)
    sync_cfg = _sync_config(company)
    if not sync_cfg or not is_shoot_event(event, sync_cfg):
        return None

    school = (event.school or "").strip()
    if not school and not event.project_id:
        return None

    actor_id = created_by_id or event.created_by_id
    status_name = sync_cfg.get("task_status", config.SCHOOL_PICTURE_STAGE_PICTURES)
    status = _default_task_status(event.company_id, status_name)
    if not status:
        return None

    project = _resolve_project(company, event, actor_id)
    if not project:
        return None

    task_name = _task_name(event)
    description = _task_description(event)
    due_date = event.event_date

    task = (
        db.session.query(Task)
        .filter(Task.calendar_event_id == event.calendar_event_id)
        .filter(Task.active.is_(True))
        .first()
    )

    if task:
        if not task.active:
            return None
        task.name = task_name
        task.description = description
        task.due_date = due_date
        task.project_id = project.project_id
        _sync_sprint_membership(task, actor_id)
        sync_school_picture_assignee(task, company)
        return task

    task = Task(
        company_id=event.company_id,
        name=task_name,
        task_status_id=status.task_status_id,
        created_by_id=actor_id,
        description=description,
        project_id=project.project_id,
        due_date=due_date,
    )
    task.calendar_event_id = event.calendar_event_id
    db.session.add(task)
    db.session.flush()
    _sync_sprint_membership(task, actor_id)
    sync_school_picture_assignee(task, company)
    return task


def prune_future_picture_day_projects(company_id):
    """
    Hide school projects that only have future picture days; show them once a
    shoot date is today or earlier. Returns True if any project was updated.
    """
    company = company_by_id(company_id)
    if not _sync_config(company):
        return False

    today = date.today()
    changed = False

    projects = (
        db.session.query(Project).filter(Project.company_id == company_id).all()
    )

    for project in projects:
        if project.user_deleted:
            continue

        calendar_tasks = (
            db.session.query(Task)
            .filter(Task.project_id == project.project_id)
            .filter(Task.calendar_event_id.isnot(None))
            .filter(Task.active.is_(True))
            .all()
        )
        if not calendar_tasks:
            continue

        has_non_calendar_tasks = (
            db.session.query(Task)
            .filter(Task.project_id == project.project_id)
            .filter(Task.calendar_event_id.is_(None))
            .filter(Task.active.is_(True))
            .first()
            is not None
        )
        if has_non_calendar_tasks:
            if not project.active:
                project.active = True
                changed = True
            continue

        has_shot_or_past = any(
            (task_shoot_date(task) or date.max) <= today for task in calendar_tasks
        )
        should_be_active = has_shot_or_past
        if project.active != should_be_active:
            project.active = should_be_active
            changed = True

    return changed


def sync_company_calendar_shoots(company_id, created_by_id=None):
    """Backfill tasks for White Raven shoot events that do not have one yet."""
    company = company_by_id(company_id)
    if not _sync_config(company):
        return 0

    linked_ids = {
        row[0]
        for row in db.session.query(Task.calendar_event_id)
        .filter(Task.company_id == company_id)
        .filter(Task.calendar_event_id.isnot(None))
        .filter(Task.active.is_(True))
        .all()
    }

    events = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.company_id == company_id)
        .filter(CalendarEvent.active.is_(True))
        .order_by(CalendarEvent.event_date.asc())
        .all()
    )

    sync_cfg = _sync_config(company)
    created = 0
    for event in events:
        if not is_shoot_event(event, sync_cfg):
            continue
        was_linked = event.calendar_event_id in linked_ids
        if sync_calendar_event_to_task(event, created_by_id) and not was_linked:
            created += 1

    promote_due_calendar_shoots_to_sprint(company_id, created_by_id)

    if created:
        db.session.commit()
    return created
