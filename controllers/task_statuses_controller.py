from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.task_statuses import TaskStatus, task_status_schema, task_statuses_schema
from util.access_control import (
    can_access_company_scoped,
    effective_company_id,
    get_actor,
    resolve_scope_company_id,
)
from util.company_workflow import company_by_id, project_board_views_for_company
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def task_statuses_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    company_id = resolve_scope_company_id(req, actor) or str(actor.company_id)
    if not validate_uuid4(company_id) or not can_access_company_scoped(actor, company_id, company_id):
        return jsonify({"message": "Forbidden"}), 403

    rows = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .order_by(TaskStatus.sort_order.asc())
        .all()
    )
    company = company_by_id(company_id)
    board_views = project_board_views_for_company(company)
    return jsonify(
        {
            "message": "task statuses found",
            "results": task_statuses_schema.dump(rows),
            "board_views": board_views,
        }
    ), 200


@authenticate_return_auth
def task_status_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    payload = req.get_json() or {}
    company_id = effective_company_id(req, actor, payload)

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    status = TaskStatus(
        company_id=company_id,
        name=payload.get("name", "New"),
        color=payload.get("color", "#64748B"),
        is_default=payload.get("is_default", False),
        sort_order=payload.get("sort_order", 0),
    )
    db.session.add(status)
    db.session.commit()
    return jsonify({"message": "task status added", "results": task_status_schema.dump(status)}), 201


@authenticate_return_auth
def task_status_update(req: Request, task_status_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(task_status_id):
        return jsonify({"message": "invalid task status id"}), 404

    status = db.session.query(TaskStatus).filter(TaskStatus.task_status_id == task_status_id).first()
    if not status:
        return jsonify({"message": "task status not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, status.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    for field in ("name", "color", "is_default", "sort_order"):
        if field in payload:
            setattr(status, field, payload[field])

    db.session.commit()
    return jsonify({"message": "task status updated", "results": task_status_schema.dump(status)}), 200
