from db import db
from models.notifications import Notification

TASK_ASSIGNED_TYPE = "task_assigned"


def notify_stage_assignment(task, assignee, stage_name, actor=None):
    """Notify the stage assignee when a school task enters their pipeline stage."""
    if not task or not assignee or not stage_name:
        return 0

    if actor and actor.user_id == assignee.user_id:
        return 0

    message = f'"{task.name}" was moved to {stage_name} and assigned to you.'
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
