from datetime import datetime

from flask import Request, Response, jsonify
from sqlalchemy.orm import joinedload

import config
from db import db
from lib.authenticate import authenticate_return_auth
from models.app_users import AppUser
from models.comments import Comment
from models.task_statuses import TaskStatus
from models.tasks import Task, task_detail_schema, task_schema
from util.access_control import (
    can_access_company,
    can_access_company_scoped,
    company_scope_filter,
    effective_company_id,
    get_actor,
    resolve_scope_company_id,
)
from util.reflection import populate_object
from util.validate_uuid4 import validate_uuid4


def _backlog_status_names(company_id=None):
    from util.company_workflow import backlog_status_names

    if company_id:
        return backlog_status_names(company_id)
    return config.project_board_views.get("backlog", ["Backlog", "Ready"])


def _parse_due_date(value):
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat"):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return "invalid"


def _return_task_to_backlog_pool(task):
    """Backlog pool = Backlog/Ready status and not assigned to any sprint."""
    status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.task_status_id == task.task_status_id)
        .first()
    )
    if status and status.name in _backlog_status_names(task.company_id):
        task.sprints.clear()


def _serialize_backlog_tasks(tasks):
    rows = []
    for task in tasks:
        data = task_schema.dump(task)
        if task.status:
            data["status"] = {
                "task_status_id": str(task.status.task_status_id),
                "name": task.status.name,
                "color": task.status.color,
            }
        data["in_sprint"] = False
        data["sprints"] = []
        rows.append(data)
    return rows


def _serialize_task_list(tasks):
    rows = []
    for task in tasks:
        data = task_schema.dump(task)
        data["in_sprint"] = len(task.sprints) > 0
        rows.append(data)
    return rows


@authenticate_return_auth
def tasks_backlog_get(req: Request, auth_info) -> Response:
    """Backlog / Ready tasks not assigned to any sprint."""
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    backlog_names = _backlog_status_names(scope)

    query = (
        db.session.query(Task)
        .join(
            TaskStatus,
            (Task.task_status_id == TaskStatus.task_status_id)
            & (Task.company_id == TaskStatus.company_id),
        )
        .options(joinedload(Task.status))
        .filter(Task.active.is_(True))
        .filter(~Task.sprints.any())
        .filter(TaskStatus.name.in_(backlog_names))
        .order_by(Task.created_at.desc())
    )
    query = company_scope_filter(query, Task, actor, scope)

    return jsonify(
        {
            "message": "backlog tasks found",
            "results": _serialize_backlog_tasks(query.all()),
        }
    ), 200


@authenticate_return_auth
def tasks_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    query = (
        db.session.query(Task)
        .options(joinedload(Task.sprints))
        .filter(Task.active.is_(True))
        .order_by(Task.created_at.desc())
    )
    scope = resolve_scope_company_id(req, actor)
    query = company_scope_filter(query, Task, actor, scope)
    return jsonify(
        {"message": "tasks found", "results": _serialize_task_list(query.all())}
    ), 200


@authenticate_return_auth
def tasks_my_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    query = (
        db.session.query(Task)
        .options(joinedload(Task.sprints))
        .filter(Task.active.is_(True))
        .filter(Task.assignees.any(AppUser.user_id == actor.user_id))
        .order_by(Task.created_at.desc())
    )
    scope = resolve_scope_company_id(req, actor)
    query = company_scope_filter(query, Task, actor, scope)
    return jsonify(
        {"message": "my tasks found", "results": _serialize_task_list(query.all())}
    ), 200


@authenticate_return_auth
def task_get_by_id(req: Request, task_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(task_id):
        return jsonify({"message": "invalid task id"}), 404

    task = _load_task_detail(task_id)
    if not task:
        return jsonify({"message": "task not found"}), 404

    if not can_access_company(actor, task.company_id):
        return jsonify({"message": "Forbidden"}), 403

    return jsonify({"message": "task found", "results": _serialize_task_detail(task)}), 200


def _load_task_detail(task_id):
    return (
        db.session.query(Task)
        .options(
            joinedload(Task.sprints),
            joinedload(Task.status),
            joinedload(Task.project),
            joinedload(Task.created_by),
            joinedload(Task.assignees),
            joinedload(Task.comments).joinedload(Comment.author),
        )
        .filter(Task.task_id == task_id)
        .first()
    )


def _serialize_task_detail(task):
    result = task_detail_schema.dump(task)
    result["in_sprint"] = len(task.sprints) > 0
    return result


def _default_status_id(company_id):
    status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .filter(TaskStatus.is_default.is_(True))
        .first()
    )
    if status:
        return status.task_status_id

    status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .order_by(TaskStatus.sort_order.asc())
        .first()
    )
    return status.task_status_id if status else None


@authenticate_return_auth
def task_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    payload = req.get_json() or {}
    company_id = effective_company_id(req, actor, payload)

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    task_status_id = payload.get("task_status_id") or _default_status_id(company_id)
    if not task_status_id:
        return jsonify({"message": "No workflow statuses configured for this company"}), 400

    due_date = _parse_due_date(payload.get("due_date"))
    if due_date == "invalid":
        return jsonify({"message": "Invalid due date"}), 400

    task = Task(
        company_id=company_id,
        name=payload.get("name", ""),
        task_status_id=task_status_id,
        created_by_id=actor.user_id,
        description=payload.get("description", ""),
        project_id=payload.get("project_id"),
        points_estimate=payload.get("points_estimate"),
        due_date=due_date,
    )
    db.session.add(task)
    db.session.commit()
    task = _load_task_detail(task.task_id)
    return jsonify({"message": "task added", "results": _serialize_task_detail(task)}), 201


@authenticate_return_auth
def task_update(req: Request, task_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(task_id):
        return jsonify({"message": "invalid task id"}), 404

    task = (
        db.session.query(Task)
        .options(joinedload(Task.assignees), joinedload(Task.sprints))
        .filter(Task.task_id == task_id)
        .first()
    )
    if not task:
        return jsonify({"message": "task not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, task.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    payload = dict(req.get_json() or {})
    assignee_id = payload.pop("assignee_id", None)

    if "due_date" in payload:
        due_date = _parse_due_date(payload.pop("due_date"))
        if due_date == "invalid":
            return jsonify({"message": "Invalid due date"}), 400
        task.due_date = due_date

    if assignee_id:
        if not validate_uuid4(assignee_id):
            return jsonify({"message": "invalid assignee id"}), 400

        user = db.session.query(AppUser).filter(AppUser.user_id == assignee_id).first()
        if not user or not can_access_company(user, task.company_id):
            return jsonify({"message": "assignee not found"}), 404

        if user in task.assignees:
            task.assignees.remove(user)
        else:
            task.assignees.append(user)

    if "task_id" in payload:
        return jsonify({"message": "update not allowed"}), 405

    error = populate_object(task, payload)
    if error:
        return error

    _return_task_to_backlog_pool(task)

    db.session.commit()
    task = _load_task_detail(task_id)
    return jsonify({"message": "task updated", "results": _serialize_task_detail(task)}), 200
