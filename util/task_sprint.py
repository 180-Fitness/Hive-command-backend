from db import db
from models.task_statuses import TaskStatus
from util.company_workflow import backlog_status_names, sprint_promote_status_name
from util.school_picture_workflow import sync_school_picture_assignee


def promote_task_entering_sprint(task):
    """Move workflow status off backlog when work enters a sprint."""
    status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.task_status_id == task.task_status_id)
        .first()
    )
    backlog_names = set(backlog_status_names(task.company_id))
    if not status or status.name not in backlog_names:
        return

    promote_name = sprint_promote_status_name(task.company_id)
    next_status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == task.company_id)
        .filter(TaskStatus.name == promote_name)
        .first()
    )
    if next_status:
        task.task_status_id = next_status.task_status_id
        sync_school_picture_assignee(task)


def add_task_to_sprint(sprint, task):
    if task not in sprint.tasks:
        sprint.tasks.append(task)
        promote_task_entering_sprint(task)


def remove_task_from_sprint(sprint, task):
    if task in sprint.tasks:
        sprint.tasks.remove(task)
