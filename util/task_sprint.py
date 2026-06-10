from db import db
from models.task_statuses import TaskStatus
from models.tasks_sprints_xref import task_sprints
from util.company_workflow import backlog_status_names, sprint_promote_status_name
from util.school_picture_workflow import sync_school_picture_assignee


def _expire_sprint_membership(sprint=None, task=None):
    if sprint is not None:
        db.session.expire(sprint, ["tasks"])
    if task is not None:
        db.session.expire(task, ["sprints"])


def sprint_has_task(sprint, task):
    return (
        db.session.query(task_sprints.c.task_id)
        .filter(
            task_sprints.c.sprint_id == sprint.sprint_id,
            task_sprints.c.task_id == task.task_id,
        )
        .first()
        is not None
    )


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
        sync_school_picture_assignee(task, notify_assignment=True)


def add_task_to_sprint(sprint, task):
    if sprint_has_task(sprint, task):
        return

    db.session.execute(
        task_sprints.insert().values(
            sprint_id=sprint.sprint_id,
            task_id=task.task_id,
        )
    )
    _expire_sprint_membership(sprint, task)
    promote_task_entering_sprint(task)


def remove_task_from_sprint(sprint, task):
    db.session.execute(
        task_sprints.delete().where(
            task_sprints.c.sprint_id == sprint.sprint_id,
            task_sprints.c.task_id == task.task_id,
        )
    )
    _expire_sprint_membership(sprint, task)


def clear_task_sprints(task):
    db.session.execute(
        task_sprints.delete().where(task_sprints.c.task_id == task.task_id)
    )
    _expire_sprint_membership(task=task)


def clear_sprint_tasks(sprint):
    db.session.execute(
        task_sprints.delete().where(task_sprints.c.sprint_id == sprint.sprint_id)
    )
    _expire_sprint_membership(sprint=sprint)
