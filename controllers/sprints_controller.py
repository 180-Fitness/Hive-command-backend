from datetime import datetime, timezone

from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.sprints import Sprint, sprint_schema, sprints_schema
from models.task_statuses import TaskStatus
from models.tasks import Task, task_schema
from util.access_control import (
    can_access_company_scoped,
    company_scope_filter,
    effective_company_id,
    get_actor,
    is_admin,
    resolve_scope_company_id,
)
from util.task_sprint import add_task_to_sprint, remove_task_from_sprint
from util.validate_uuid4 import validate_uuid4
_SPRINT_METADATA_FIELDS = frozenset({"name", "start_date", "end_date", "active"})


def _sprint_deadline_has_passed(sprint):
    if not sprint.end_date:
        return False
    end = sprint.end_date
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    today = datetime.now(timezone.utc).date()
    return end.date() < today


def _archive_sprint(sprint):
    sprint.active = False
    sprint.tasks.clear()


def _archive_expired_sprints(actor, scope_company_id=None):
    query = (
        db.session.query(Sprint)
        .filter(Sprint.active.is_(True))
        .filter(Sprint.end_date.isnot(None))
    )
    query = company_scope_filter(query, Sprint, actor, scope_company_id)
    archived = False
    for sprint in query.all():
        if _sprint_deadline_has_passed(sprint):
            _archive_sprint(sprint)
            archived = True
    if archived:
        db.session.commit()


def _serialize_sprint_task(task):
    data = task_schema.dump(task)
    data["in_sprint"] = True
    return data


def _sprint_with_tasks(sprint):
    data = sprint_schema.dump(sprint)
    data["tasks"] = [_serialize_sprint_task(task) for task in sprint.tasks]
    return data


@authenticate_return_auth
def sprints_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    if scope:
        from util.weekly_sprints import (
            ensure_weekly_sprint_rollover,
            sync_due_tasks_into_current_week_sprint,
            uses_weekly_sprints,
        )

        if uses_weekly_sprints(scope):
            ensure_weekly_sprint_rollover(scope, actor.user_id)
            sync_due_tasks_into_current_week_sprint(scope, actor.user_id)

    _archive_expired_sprints(actor, scope)

    query = (
        db.session.query(Sprint)
        .filter(Sprint.active.is_(True))
        .order_by(Sprint.created_at.desc(), Sprint.name.asc())
    )
    query = company_scope_filter(query, Sprint, actor, scope)
    rows = query.all()
    results = []
    for sprint in rows:
        results.append(_sprint_with_tasks(sprint))
    return jsonify({"message": "sprints found", "results": results}), 200


@authenticate_return_auth
def sprint_get_by_id(req: Request, sprint_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(sprint_id):
        return jsonify({"message": "invalid sprint id"}), 404

    sprint = db.session.query(Sprint).filter(Sprint.sprint_id == sprint_id).first()
    if not sprint:
        return jsonify({"message": "sprint not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, sprint.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    if scope:
        from util.weekly_sprints import (
            ensure_weekly_sprint_rollover,
            uses_weekly_sprints,
        )

        if uses_weekly_sprints(scope):
            ensure_weekly_sprint_rollover(scope, actor.user_id)

    if not sprint.active:
        return jsonify({"message": "This sprint has been archived"}), 404

    if _sprint_deadline_has_passed(sprint):
        _archive_sprint(sprint)
        db.session.commit()
        return jsonify({"message": "This sprint has been archived"}), 404

    return jsonify({"message": "sprint found", "results": _sprint_with_tasks(sprint)}), 200


@authenticate_return_auth
def sprint_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    payload = req.get_json() or {}
    company_id = effective_company_id(req, actor, payload)

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    sprint = Sprint(
        company_id=company_id,
        name=payload.get("name", "").strip() or "Sprint",
        created_by_id=actor.user_id,
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
    )
    db.session.add(sprint)
    db.session.commit()
    return jsonify({"message": "sprint added", "results": _sprint_with_tasks(sprint)}), 201


@authenticate_return_auth
def sprint_update(req: Request, sprint_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(sprint_id):
        return jsonify({"message": "invalid sprint id"}), 404

    sprint = db.session.query(Sprint).filter(Sprint.sprint_id == sprint_id).first()
    if not sprint or not sprint.active:
        return jsonify({"message": "sprint not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, sprint.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}

    metadata_updates = [
        field
        for field in _SPRINT_METADATA_FIELDS
        if field in payload and field not in ("task_id", "task_ids", "action")
    ]
    if metadata_updates and not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    task_id = payload.get("task_id")
    if task_id and validate_uuid4(task_id):
        task = db.session.query(Task).filter(Task.task_id == task_id).first()
        if task and can_access_company_scoped(actor, task.company_id, scope):
            if str(task.company_id) == str(sprint.company_id):
                if task in sprint.tasks:
                    remove_task_from_sprint(sprint, task)
                else:
                    add_task_to_sprint(sprint, task)

    task_ids = payload.get("task_ids")
    if task_ids and isinstance(task_ids, list):
        tasks = (
            db.session.query(Task)
            .filter(Task.task_id.in_(task_ids))
            .filter(Task.active.is_(True))
            .all()
        )
        for task in tasks:
            if not can_access_company_scoped(actor, task.company_id, scope):
                continue
            if str(task.company_id) != str(sprint.company_id):
                continue
            if payload.get("action") == "remove":
                remove_task_from_sprint(sprint, task)
            else:
                add_task_to_sprint(sprint, task)

    for field in metadata_updates:
        setattr(sprint, field, payload[field])

    db.session.commit()
    return jsonify({"message": "sprint updated", "results": _sprint_with_tasks(sprint)}), 200


@authenticate_return_auth
def sprint_delete(req: Request, sprint_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(sprint_id):
        return jsonify({"message": "invalid sprint id"}), 404

    sprint = db.session.query(Sprint).filter(Sprint.sprint_id == sprint_id).first()
    if not sprint:
        return jsonify({"message": "sprint not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, sprint.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    sprint.tasks.clear()
    db.session.delete(sprint)
    db.session.commit()
    return jsonify({"message": "sprint deleted"}), 200
