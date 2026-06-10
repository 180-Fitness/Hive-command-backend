from datetime import date

from flask import Request, Response, jsonify
from sqlalchemy.orm import joinedload

from db import db
from lib.authenticate import authenticate_return_auth
from models.companies import Company
from models.tasks import Task
from util.access_control import (
    can_access_company_scoped,
    get_actor,
    is_admin,
    resolve_scope_company_id,
)
from util.school_picture_workflow import build_school_shoot_delivery_report


@authenticate_return_auth
def school_shoot_delivery_report_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    scope = resolve_scope_company_id(req, actor)
    if not scope:
        return jsonify({"message": "Select a company to view this report"}), 400

    if not can_access_company_scoped(actor, scope, scope):
        return jsonify({"message": "Forbidden"}), 403

    company = (
        db.session.query(Company)
        .filter(Company.company_id == scope)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        return jsonify({"message": "Company not found"}), 404

    month = (req.args.get("month") or "").strip() or None
    if month:
        try:
            year, month_num = month.split("-", 1)
            date(int(year), int(month_num), 1)
        except (TypeError, ValueError):
            return jsonify({"message": "month must be YYYY-MM"}), 400

    tasks = (
        db.session.query(Task)
        .options(joinedload(Task.status), joinedload(Task.project))
        .filter(Task.active.is_(True))
        .filter(Task.company_id == scope)
        .all()
    )

    report = build_school_shoot_delivery_report(
        tasks, date.today(), company, month=month
    )

    return (
        jsonify(
            {
                "message": "School shoot delivery report",
                "results": {
                    **report,
                    "company_id": str(company.company_id),
                    "company_name": company.name,
                    "month": month,
                },
            }
        ),
        200,
    )
