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
from util.company_workflow import company_has_school_picture_tasks
from util.reflection import populate_object
from util.school_picture_workflow import (
    attach_school_picture_fields,
    is_school_picture_task,
    school_shoot_dashboard_meta,
)
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


def _serialize_assignees(task):
    if not task.assignees:
        return []
    return [
        {
            "user_id": str(assignee.user_id),
            "first_name": assignee.first_name,
            "last_name": assignee.last_name,
            "color": assignee.color,
        }
        for assignee in task.assignees
    ]


def _attach_school_picture_dashboard_fields(data, task):
    data = attach_school_picture_fields(data, task)
    if not is_school_picture_task(task):
        return data

    data.update(school_shoot_dashboard_meta(task))
    if task.project and (task.project.name or "").strip():
        data["school_name"] = task.project.name.strip()
    data["assignees"] = _serialize_assignees(task)
    return data


def _enrich_task_row(task, data, *, in_sprint=None):
    if task.status:
        data["status"] = {
            "task_status_id": str(task.status.task_status_id),
            "name": task.status.name,
            "color": task.status.color,
        }
    if in_sprint is not None:
        data["in_sprint"] = in_sprint
    elif "in_sprint" not in data:
        data["in_sprint"] = len(task.sprints) > 0
    return _attach_school_picture_dashboard_fields(data, task)


def _serialize_backlog_tasks(tasks):
    rows = []
    for task in tasks:
        data = _enrich_task_row(task, task_schema.dump(task), in_sprint=False)
        data["sprints"] = []
        rows.append(data)
    return rows


def _serialize_task_list(tasks):
    rows = []
    for task in tasks:
        rows.append(_enrich_task_row(task, task_schema.dump(task)))
    return rows


def _serialize_school_picture_tasks(tasks):
    from util.white_raven_calendar_sync import task_shoot_date

    rows = []
    for task in tasks:
        data = _enrich_task_row(task, task_schema.dump(task))
        shoot_date = task_shoot_date(task)
        if shoot_date:
            data["shoot_date"] = shoot_date.isoformat()
        rows.append(data)
    return rows


@authenticate_return_auth
def tasks_backlog_get(req: Request, auth_info) -> Response:
    """Backlog / Ready tasks not assigned to any sprint."""
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    if scope:
        from util.white_raven_calendar_sync import promote_due_calendar_shoots_to_sprint

        promote_due_calendar_shoots_to_sprint(scope, actor.user_id)

    backlog_names = _backlog_status_names(scope)

    query = (
        db.session.query(Task)
        .join(
            TaskStatus,
            (Task.task_status_id == TaskStatus.task_status_id)
            & (Task.company_id == TaskStatus.company_id),
        )
        .options(
            joinedload(Task.status),
            joinedload(Task.project),
            joinedload(Task.assignees),
        )
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
        .options(
            joinedload(Task.sprints),
            joinedload(Task.status),
            joinedload(Task.project),
            joinedload(Task.assignees),
        )
        .filter(Task.active.is_(True))
        .order_by(Task.created_at.desc())
    )
    scope = resolve_scope_company_id(req, actor)
    if scope and company_has_school_picture_tasks(scope):
        query = query.filter(Task.calendar_event_id.is_(None))
    query = company_scope_filter(query, Task, actor, scope)
    return jsonify(
        {"message": "tasks found", "results": _serialize_task_list(query.all())}
    ), 200


@authenticate_return_auth
def tasks_school_pictures_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    if not scope or not company_has_school_picture_tasks(scope):
        return jsonify({"message": "school picture tasks not available", "results": []}), 200

    from models.calendar_events import CalendarEvent
    from util.white_raven_calendar_sync import promote_due_calendar_shoots_to_sprint

    promote_due_calendar_shoots_to_sprint(scope, actor.user_id)

    query = (
        db.session.query(Task)
        .options(
            joinedload(Task.sprints),
            joinedload(Task.status),
            joinedload(Task.assignees),
        )
        .outerjoin(
            CalendarEvent,
            Task.calendar_event_id == CalendarEvent.calendar_event_id,
        )
        .filter(Task.active.is_(True))
        .filter(Task.calendar_event_id.isnot(None))
        .order_by(CalendarEvent.event_date.asc().nullslast(), Task.name.asc())
    )
    query = company_scope_filter(query, Task, actor, scope)

    return jsonify(
        {
            "message": "school picture tasks found",
            "results": _serialize_school_picture_tasks(query.all()),
        }
    ), 200


@authenticate_return_auth
def tasks_my_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    week_start = week_end = None
    if scope:
        from util.weekly_sprints import (
            ensure_weekly_sprint_rollover,
            my_tasks_current_week_only,
            sync_due_tasks_into_current_week_sprint,
        )

        if my_tasks_current_week_only(scope):
            ensure_weekly_sprint_rollover(scope, actor.user_id)
            sync_due_tasks_into_current_week_sprint(scope, actor.user_id)
            from util.task_workload import week_bounds

            week_start, week_end = week_bounds()

    query = (
        db.session.query(Task)
        .options(
            joinedload(Task.sprints),
            joinedload(Task.status),
            joinedload(Task.project),
            joinedload(Task.assignees),
        )
        .filter(Task.active.is_(True))
        .filter(Task.assignees.any(AppUser.user_id == actor.user_id))
        .order_by(Task.created_at.desc())
    )
    if week_start and week_end:
        query = (
            query.filter(Task.due_date.isnot(None))
            .filter(Task.due_date >= week_start)
            .filter(Task.due_date <= week_end)
        )
    query = company_scope_filter(query, Task, actor, scope)

    payload = {
        "message": "my tasks found",
        "results": _serialize_task_list(query.all()),
    }
    if week_start and week_end:
        payload["week_start"] = week_start.isoformat()
        payload["week_end"] = week_end.isoformat()
    return jsonify(payload), 200


@authenticate_return_auth
def task_get_by_id(req: Request, task_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(task_id):
        return jsonify({"message": "invalid task id"}), 404

    task = _load_task_detail(task_id)
    if not task or not task.active:
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
    result["is_school_task"] = task.calendar_event_id is not None
    return _attach_school_picture_dashboard_fields(result, task)


def _is_transition_to_done(task, new_status_id):
    from util.company_workflow import done_status_names

    new_status = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.task_status_id == new_status_id)
        .filter(TaskStatus.company_id == task.company_id)
        .first()
    )
    if not new_status:
        return False
    return new_status.name in done_status_names(task.company_id)


def _validate_school_done_delivery(task, new_status_id):
    if not task.calendar_event_id:
        return None
    if not new_status_id or not _is_transition_to_done(task, new_status_id):
        return None
    if task.delivery_date is not None:
        return None
    return jsonify({"message": "Delivery date is required when marking a school task done"}), 400


def _apply_delivery_fields(task, payload):
    if "delivery_date" not in payload and "delivery_picked_up_by" not in payload:
        return None

    if "delivery_date" in payload:
        delivery_date = _parse_due_date(payload.pop("delivery_date"))
        if delivery_date == "invalid":
            return jsonify({"message": "Invalid delivery date"}), 400
        task.delivery_date = delivery_date
        if delivery_date is None:
            task.delivery_picked_up_by = ""

    if "delivery_picked_up_by" in payload:
        if task.delivery_date is None:
            return jsonify({"message": "Delivery date is required"}), 400
        task.delivery_picked_up_by = (payload.pop("delivery_picked_up_by") or "").strip()

    return None


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
        .options(
            joinedload(Task.assignees),
            joinedload(Task.sprints),
            joinedload(Task.status),
        )
        .filter(Task.task_id == task_id)
        .first()
    )
    if not task or not task.active:
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

    delivery_error = _apply_delivery_fields(task, payload)
    if delivery_error:
        return delivery_error

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

    if "task_status_id" in payload:
        from util.company_workflow import validate_mark_done_transition

        current_name = task.status.name if task.status else None
        status_error = validate_mark_done_transition(
            task.company_id, current_name, payload["task_status_id"]
        )
        if status_error:
            return jsonify({"message": status_error}), 400

        delivery_error = _validate_school_done_delivery(task, payload["task_status_id"])
        if delivery_error:
            return delivery_error

    error = populate_object(task, payload)
    if error:
        return error

    if "task_status_id" in payload:
        from util.school_picture_workflow import sync_school_picture_assignee

        sync_school_picture_assignee(task)

    _return_task_to_backlog_pool(task)

    db.session.commit()
    task = _load_task_detail(task_id)
    return jsonify({"message": "task updated", "results": _serialize_task_detail(task)}), 200


@authenticate_return_auth
def task_delete(req: Request, task_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(task_id):
        return jsonify({"message": "invalid task id"}), 404

    task = (
        db.session.query(Task)
        .filter(Task.task_id == task_id)
        .first()
    )
    if not task or not task.active:
        return jsonify({"message": "task not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, task.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    task.active = False
    db.session.commit()
    return jsonify({"message": "task deleted"}), 200
