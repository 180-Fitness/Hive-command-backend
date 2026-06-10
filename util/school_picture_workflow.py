from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import joinedload

import config
from db import db
from models.app_users import AppUser
from models.task_statuses import TaskStatus
from util.access_control import can_access_company
from util.company_workflow import company_by_id
from util.task_workload import is_done_status_name


def _normalized_name(value):
    return (value or "").strip().casefold()


def _calendar_sync_config(company):
    if not company:
        return None
    return config.company_calendar_task_sync.get(company.name)


def _stage_assignee_cfg(company, status_name):
    sync_cfg = _calendar_sync_config(company) or {}
    stage_assignees = sync_cfg.get("stage_assignees") or {}
    cfg = stage_assignees.get((status_name or "").strip())
    if cfg:
        return cfg
    return sync_cfg.get("assignee")


def _find_assignee(company_id, assignee_cfg):
    if not assignee_cfg:
        return None

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


def _task_status_name(task):
    if task.status and task.status.task_status_id == task.task_status_id:
        return (task.status.name or "").strip()

    return (
        db.session.query(TaskStatus.name)
        .filter(TaskStatus.task_status_id == task.task_status_id)
        .scalar()
        or ""
    ).strip()


def sync_school_picture_assignee(task, company=None, actor=None, notify_assignment=False):
    """Assign school-picture tasks to the owner for their current pipeline stage."""
    if not is_school_picture_task(task):
        return False

    status_name = _task_status_name(task)
    if is_done_status_name(status_name):
        return False

    if status_name == config.SCHOOL_PICTURE_STAGE_UPCOMING:
        previous_id = task.assignees[0].user_id if len(task.assignees) == 1 else None
        task.assignees.clear()
        return previous_id is not None

    company = company or company_by_id(task.company_id)
    assignee_cfg = _stage_assignee_cfg(company, status_name)
    assignee = _find_assignee(task.company_id, assignee_cfg)
    if not assignee:
        return False

    previous_id = task.assignees[0].user_id if len(task.assignees) == 1 else None
    task.assignees.clear()
    task.assignees.append(assignee)
    changed = previous_id != assignee.user_id

    if notify_assignment and changed:
        from util.task_assignment_notifications import notify_stage_assignment

        notify_stage_assignment(task, assignee, status_name, actor)

    return changed


def sync_all_school_picture_assignees(company_id):
    from models.tasks import Task

    company = company_by_id(company_id)
    if not _calendar_sync_config(company):
        return 0

    tasks = (
        db.session.query(Task)
        .options(joinedload(Task.status), joinedload(Task.assignees))
        .filter(Task.company_id == company_id)
        .filter(Task.calendar_event_id.isnot(None))
        .filter(Task.active.is_(True))
        .all()
    )

    updated = 0
    for task in tasks:
        if sync_school_picture_assignee(task, company):
            updated += 1

    if updated:
        db.session.commit()
    return updated


def pipeline_config(company):
    if not company:
        return None
    return config.school_picture_pipeline.get(company.name)


def is_school_picture_task(task):
    return bool(task and task.calendar_event_id)


def finalize_deadline_weeks(company):
    if not company:
        return 3
    cfg = pipeline_config(company)
    if cfg:
        return cfg.get("finalize_deadline_weeks", 3)
    sync_cfg = config.company_calendar_task_sync.get(company.name, {})
    return sync_cfg.get("finalize_deadline_weeks", 3)


def picture_date(task):
    if not is_school_picture_task(task):
        return None
    return task.due_date


def finalize_due_date(task, company=None):
    shoot = picture_date(task)
    if not shoot:
        return None
    company = company or company_by_id(task.company_id)
    return shoot + timedelta(weeks=finalize_deadline_weeks(company))


def pipeline_stage_defs(company):
    cfg = pipeline_config(company)
    if cfg:
        return cfg.get("stages", [])

    custom = config.company_task_statuses.get(company.name if company else "", [])
    return [{"name": entry["name"], "color": entry.get("color")} for entry in custom]


def build_pipeline_payload(task, company=None):
    company = company or company_by_id(task.company_id)
    stages = pipeline_stage_defs(company)
    current_name = (task.status.name if task.status else "").strip()
    current_index = -1

    for index, stage in enumerate(stages):
        if stage["name"] == current_name:
            current_index = index
            break

    pipeline = []
    for index, stage in enumerate(stages):
        state = "upcoming"
        if current_index >= 0:
            if index < current_index:
                state = "complete"
            elif index == current_index:
                state = "current"
        pipeline.append(
            {
                "name": stage["name"],
                "color": stage.get("color"),
                "state": state,
            }
        )

    shoot = picture_date(task)
    finalize = finalize_due_date(task, company)

    return {
        "is_school_picture": True,
        "picture_date": shoot.isoformat() if shoot else None,
        "finalize_due_date": finalize.isoformat() if finalize else None,
        "finalize_deadline_weeks": finalize_deadline_weeks(company),
        "current_stage": current_name or None,
        "pipeline": pipeline,
    }


def attach_school_picture_fields(data, task, company=None):
    if not is_school_picture_task(task):
        return data

    company = company or company_by_id(task.company_id)
    payload = build_pipeline_payload(task, company)
    bucket_date = dashboard_bucket_date(task)
    data["school_picture"] = payload
    data["finalize_due_date"] = payload["finalize_due_date"]
    if bucket_date:
        data["dashboard_due_date"] = bucket_date.isoformat()
    return data


def dashboard_bucket_date(task, today=None):
    """Which date drives due-today / this-week buckets for dashboard views."""
    today = today or date.today()

    if not is_school_picture_task(task):
        return task.due_date

    shoot = task.due_date
    if not shoot:
        return None

    if shoot > today:
        return shoot

    return finalize_due_date(task)


def school_picture_in_pipeline(task, today=None):
    today = today or date.today()
    if not is_school_picture_task(task):
        return False
    if task.status and is_done_status_name(task.status.name):
        return False

    shoot = task.due_date
    return bool(shoot and shoot <= today)


CLOSING_DAYS = 14


def days_until_finalize(task, today=None, company=None):
    finalize = finalize_due_date(task, company)
    if not finalize:
        return None
    today = today or date.today()
    return (finalize - today).days


def school_shoot_dashboard_meta(task, today=None, company=None):
    """Card outline + countdown colors for the TV school-picture dashboard."""
    today = today or date.today()
    company = company or company_by_id(task.company_id)
    shoot = picture_date(task)
    finalize = finalize_due_date(task, company)
    done = bool(task.status and is_done_status_name(task.status.name))
    days_remaining = days_until_finalize(task, today, company)
    completed_on = None

    if done:
        card_state = "finished"
        if task.updated_at:
            completed_on = (
                task.updated_at.date()
                if hasattr(task.updated_at, "date")
                else task.updated_at
            )
        else:
            completed_on = today
        if finalize and completed_on <= finalize:
            countdown_state = "on_time"
        else:
            countdown_state = "late"
    elif finalize is None:
        card_state = "on_track"
        countdown_state = "early"
    elif days_remaining < 0:
        card_state = "overdue"
        countdown_state = "late"
    elif days_remaining <= CLOSING_DAYS:
        card_state = "closing"
        countdown_state = "early"
    else:
        card_state = "on_track"
        countdown_state = "early"

    # Finalize countdown only applies after picture day (matches TV dashboard).
    display_days_remaining = days_remaining
    if shoot and shoot > today and not done:
        display_days_remaining = None

    return {
        "card_state": card_state,
        "countdown_state": countdown_state,
        "days_remaining": display_days_remaining,
        "completed_on": completed_on.isoformat() if completed_on else None,
    }


def shoot_delivery_timing(task, today=None, company=None):
    """Report bucket for shot schools: early, on_time, or late."""
    today = today or date.today()
    company = company or company_by_id(task.company_id)
    finalize = finalize_due_date(task, company)
    done = bool(task.status and is_done_status_name(task.status.name))

    if done:
        if task.updated_at:
            completed_on = (
                task.updated_at.date()
                if hasattr(task.updated_at, "date")
                else task.updated_at
            )
        else:
            completed_on = today
        if not finalize:
            return "on_time"
        if completed_on < finalize:
            return "early"
        if completed_on == finalize:
            return "on_time"
        return "late"

    days = days_until_finalize(task, today, company)
    if days is None:
        return "early"
    if days < 0:
        return "late"
    if days == 0:
        return "on_time"
    return "early"


def _timing_pct(count, total):
    if not total:
        return 0.0
    return round(count / total * 100, 1)


def _report_timing(timing):
    """Collapse early into on_time for the delivery report."""
    if timing == "early":
        return "on_time"
    if timing in ("on_time", "late"):
        return timing
    return "on_time"


def _timing_summary(rows):
    total = len(rows)
    counts = {"on_time": 0, "late": 0}
    for row in rows:
        timing = _report_timing(row.get("delivery_timing"))
        counts[timing] += 1
    return {
        "total": total,
        "counts": counts,
        "percentages": {key: _timing_pct(counts[key], total) for key in counts},
    }


def _school_name(task):
    from util.white_raven_calendar_sync import task_school_name

    return task_school_name(task)


def _completed_on_date(task, today=None):
    today = today or date.today()
    if task.updated_at:
        return (
            task.updated_at.date()
            if hasattr(task.updated_at, "date")
            else task.updated_at
        )
    return today


def _serialize_report_row(task, today, company):
    timing = shoot_delivery_timing(task, today, company)
    done = bool(task.status and is_done_status_name(task.status.name))
    shoot = picture_date(task)
    row = {
        "task_id": str(task.task_id),
        "school_name": _school_name(task),
        "picture_date": shoot.isoformat() if shoot else None,
        "delivery_timing": timing,
        "is_finished": done,
    }
    if done:
        completed_on = _completed_on_date(task, today)
        row["completed_on"] = completed_on.isoformat()
    return row


def _finished_schools_list(rows):
    finished = [row for row in rows if row.get("is_finished")]
    finished.sort(
        key=lambda row: (
            row.get("completed_on") or "",
            row.get("school_name") or "",
        ),
        reverse=True,
    )
    return [
        {
            "task_id": row["task_id"],
            "school_name": row["school_name"],
            "picture_date": row.get("picture_date"),
            "completed_on": row.get("completed_on"),
            "delivery_timing": _report_timing(row.get("delivery_timing")),
        }
        for row in finished
    ]


def _month_bounds(month):
    """Return inclusive start/end dates for a YYYY-MM string."""
    if not month:
        return None, None
    year, month_num = month.split("-", 1)
    start = date(int(year), int(month_num), 1)
    if int(month_num) == 12:
        end = date(int(year) + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(int(year), int(month_num) + 1, 1) - timedelta(days=1)
    return start, end


def build_school_shoot_delivery_report(tasks, today=None, company=None, month=None):
    """Aggregate on-time / late percentages for schools already shot."""
    today = today or date.today()
    month_start, month_end = _month_bounds(month)
    rows = []

    for task in tasks:
        if not is_school_picture_task(task):
            continue
        shoot = picture_date(task)
        if not shoot or shoot > today:
            continue
        if month_start and month_end and not (month_start <= shoot <= month_end):
            continue

        task_company = company or company_by_id(task.company_id)
        rows.append(_serialize_report_row(task, today, task_company))

    finished = [row for row in rows if row["is_finished"]]
    in_progress = [row for row in rows if not row["is_finished"]]

    return {
        "as_of": today.isoformat(),
        "overall": _timing_summary(rows),
        "finished": _timing_summary(finished),
        "in_progress": _timing_summary(in_progress),
        "finished_schools": _finished_schools_list(rows),
    }
