from db import db
from models.notifications import Notification

TASK_ASSIGNED_TYPE = "task_assigned"


def _finalize_countdown_suffix(task):
    from util.school_picture_workflow import (
        days_until_finalize,
        finalize_deadline_weeks,
        finalize_due_date,
    )
    from util.company_workflow import company_by_id

    company = company_by_id(task.company_id)
    days = days_until_finalize(task, company=company)
    finalize = finalize_due_date(task, company)
    if days is None or finalize is None:
        return ""

    weeks = finalize_deadline_weeks(company)
    due_label = finalize.strftime("%b %d, %Y")
    if days < 0:
        overdue = abs(days)
        unit = "day" if overdue == 1 else "days"
        return (
            f" The {weeks}-week deadline passed {overdue} {unit} ago ({due_label})."
        )
    if days == 0:
        return f" The {weeks}-week deadline is today ({due_label})."
    if days == 1:
        return f" 1 day left until the {weeks}-week deadline ({due_label})."
    return f" {days} days left until the {weeks}-week deadline ({due_label})."


def notify_stage_assignment(
    task, assignee, stage_name, actor=None, include_finalize_countdown=False
):
    """Notify the stage assignee when a school task enters their pipeline stage."""
    if not task or not assignee or not stage_name:
        return 0

    if actor and actor.user_id == assignee.user_id:
        return 0

    suffix = _finalize_countdown_suffix(task) if include_finalize_countdown else ""
    message = f'"{task.name}" was moved to {stage_name} and assigned to you.{suffix}'
    link = f"/task/{task.task_id}"

    db.session.add(
        Notification(
            receiver_id=assignee.user_id,
            company_id=task.company_id,
            notification_type=TASK_ASSIGNED_TYPE,
            message=message,
            link=link,
        )
    )
    return 1
