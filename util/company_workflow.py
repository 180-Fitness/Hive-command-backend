from random import choice

import config
from db import db, query
from models.companies import Company
from models.task_statuses import TaskStatus
from models.tasks import Task


def company_by_id(company_id):
    return query(Company).filter(Company.company_id == company_id).first()


def company_has_school_picture_tasks(company_id):
    company = company_by_id(company_id)
    if not company:
        return False
    return company.name in config.company_calendar_task_sync


def task_status_defs_for_company(company):
    if not company:
        return config.default_task_statuses
    custom = config.company_task_statuses.get(company.name)
    if custom:
        return custom
    return [
        {"name": name, "color": choice(config.palette)}
        for name in config.default_task_statuses
    ]


def project_board_views_for_company(company):
    if company and company.name in config.company_project_board_views:
        return config.company_project_board_views[company.name]
    return config.project_board_views


def backlog_status_names(company_id):
    company = company_by_id(company_id)
    views = project_board_views_for_company(company)
    return views.get("backlog", ["Backlog", "Ready"])


def working_status_names(company_id):
    company = company_by_id(company_id)
    views = project_board_views_for_company(company)
    return views.get("working", ["In Progress", "In Review", "Blocked"])


def sprint_promote_status_name(company_id):
    company = company_by_id(company_id)
    views = project_board_views_for_company(company)
    if views.get("sprint_promote_to"):
        return views["sprint_promote_to"]
    working = working_status_names(company_id)
    return working[0] if working else "In Progress"


def done_status_names(company_id=None):
    if company_id:
        company = company_by_id(company_id)
        views = project_board_views_for_company(company)
        return views.get("done", ["Done"])
    return config.project_board_views.get("done", ["Done"])


def mark_done_requires_status(company_id):
    company = company_by_id(company_id)
    views = project_board_views_for_company(company)
    return views.get("mark_done_requires_status")


def validate_mark_done_transition(company_id, current_status_name, new_status_id):
    """Return an error message if a done transition is not allowed."""
    required = mark_done_requires_status(company_id)
    if not required:
        return None

    new_status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.task_status_id == new_status_id)
        .filter(TaskStatus.company_id == company_id)
        .first()
    )
    if not new_status:
        return None

    done_names = set(done_status_names(company_id))
    if new_status.name not in done_names:
        return None

    if (current_status_name or "").strip() != required:
        return f'Task must be in "{required}" before it can be marked done'

    return None


def sync_company_task_statuses(company):
    """Apply configured workflow statuses for companies with custom definitions."""
    defs = config.company_task_statuses.get(company.name)
    if not defs:
        return

    existing = (
        query(TaskStatus).filter(TaskStatus.company_id == company.company_id).all()
    )
    existing_by_name = {status.name: status for status in existing}
    desired_names = {defn["name"] for defn in defs}

    for old_name, new_name in config.company_task_status_renames.get(
        company.name, {}
    ).items():
        if old_name in existing_by_name and new_name not in existing_by_name:
            status = existing_by_name.pop(old_name)
            status.name = new_name
            existing_by_name[new_name] = status

    db.session.flush()

    default_status = None
    for index, defn in enumerate(defs):
        name = defn["name"]
        if name in existing_by_name:
            status = existing_by_name[name]
            status.sort_order = index
            status.color = defn.get("color", status.color)
            status.is_default = index == 0
            if index == 0:
                default_status = status
        else:
            status = TaskStatus(
                company_id=company.company_id,
                name=name,
                color=defn.get("color", choice(config.palette)),
                is_default=index == 0,
                sort_order=index,
            )
            db.session.add(status)
            if index == 0:
                default_status = status

    db.session.flush()

    if not default_status:
        default_status = (
            query(TaskStatus)
            .filter(TaskStatus.company_id == company.company_id)
            .order_by(TaskStatus.sort_order.asc())
            .first()
        )

    for status in existing:
        if status.name in desired_names:
            continue
        if default_status:
            (
                db.session.query(Task)
                .filter(Task.task_status_id == status.task_status_id)
                .update(
                    {"task_status_id": default_status.task_status_id},
                    synchronize_session=False,
                )
            )
        db.session.delete(status)

    db.session.commit()
