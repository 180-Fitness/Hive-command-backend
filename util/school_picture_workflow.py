from datetime import date, timedelta

import config
from util.company_workflow import company_by_id
from util.task_workload import is_done_status_name


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
