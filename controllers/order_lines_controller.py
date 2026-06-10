from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.order_lines import OrderLine, order_lines_schema
from models.tasks import Task
from util.access_control import (
    can_access_company_scoped,
    effective_company_id,
    get_actor,
    is_admin,
    resolve_scope_company_id,
)
from util.proofpix_order_sync import import_proofpix_orders, parse_proofpix_csv
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def order_lines_by_task_get(req: Request, auth_info, task_id) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(task_id):
        return jsonify({"message": "invalid task id"}), 404

    task = (
        db.session.query(Task)
        .filter(Task.task_id == task_id)
        .filter(Task.active.is_(True))
        .first()
    )
    if not task:
        return jsonify({"message": "task not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, task.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    lines = (
        db.session.query(OrderLine)
        .filter(OrderLine.task_id == task_id)
        .filter(OrderLine.active.is_(True))
        .order_by(
            OrderLine.bill_last_name.asc(),
            OrderLine.bill_first_name.asc(),
            OrderLine.product_name.asc(),
        )
        .all()
    )

    return jsonify(
        {
            "message": "order lines found",
            "results": order_lines_schema.dump(lines),
        }
    ), 200


@authenticate_return_auth
def proofpix_orders_import(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    upload = req.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"message": "A CSV file is required"}), 400

    filename = upload.filename.lower()
    if not filename.endswith(".csv"):
        return jsonify({"message": "File must be a .csv export"}), 400

    company_id = effective_company_id(req, actor)
    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    try:
        rows = parse_proofpix_csv(upload)
        results = import_proofpix_orders(company_id, rows)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"message": f"Could not import CSV: {exc}"}), 400

    return jsonify(
        {
            "message": "proofpix orders imported",
            "results": {
                **results,
                "filename": upload.filename,
            },
        }
    ), 200
