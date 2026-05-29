from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.task_statuses import TaskStatus, task_status_schema, task_statuses_schema
from util.access_control import can_access_company, get_actor
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def task_statuses_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    company_id = req.args.get("company_id") or str(actor.company_id)
    if not validate_uuid4(company_id) or not can_access_company(actor, company_id):
        return jsonify({"message": "Forbidden"}), 403

    rows = (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .order_by(TaskStatus.sort_order.asc())
        .all()
    )
    return jsonify({"message": "task statuses found", "results": task_statuses_schema.dump(rows)}), 200


@authenticate_return_auth
def task_status_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    payload = req.get_json() or {}
    company_id = payload.get("company_id", actor.company_id)

    if not can_access_company(actor, company_id):
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

    if not can_access_company(actor, status.company_id):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    for field in ("name", "color", "is_default", "sort_order"):
        if field in payload:
            setattr(status, field, payload[field])

    db.session.commit()
    return jsonify({"message": "task status updated", "results": task_status_schema.dump(status)}), 200
