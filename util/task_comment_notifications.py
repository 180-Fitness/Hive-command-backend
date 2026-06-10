from db import db
from models.notifications import Notification

TASK_COMMENT_TYPE = "task_comment"
_PREVIEW_MAX = 100


def _author_display_name(user):
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return name or "Someone"


def _comment_preview(body):
    text = (body or "").strip()
    if len(text) <= _PREVIEW_MAX:
        return text
    return text[: _PREVIEW_MAX - 1].rstrip() + "…"


def notify_task_assignees_of_comment(task, comment, author):
    """Notify every assignee except the comment author."""
    if not task or not comment or not author:
        return 0

    author_name = _author_display_name(author)
    preview = _comment_preview(comment.body)
    message = f'{author_name} commented on "{task.name}": {preview}'
    link = f"/task/{task.task_id}"

    created = 0
    for assignee in task.assignees or []:
        if assignee.user_id == author.user_id:
            continue
        db.session.add(
            Notification(
                receiver_id=assignee.user_id,
                company_id=task.company_id,
                notification_type=TASK_COMMENT_TYPE,
                message=message,
                link=link,
            )
        )
        created += 1
    return created
