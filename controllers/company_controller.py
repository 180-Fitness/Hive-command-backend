from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.companies import Company, company_schema, companies_schema
from util.access_control import (
    can_access_company_scoped,
    get_actor,
    is_enterprise_admin,
    resolve_scope_company_id,
)
from util.company_seed import ensure_company_task_statuses
from util.phone import normalize_phone
from util.reflection import populate_object
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def companies_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    query = db.session.query(Company).filter(Company.active.is_(True)).order_by(Company.name.asc())
    if is_enterprise_admin(actor):
        query = query.filter(Company.enterprise_id == actor.enterprise_id)
    else:
        query = query.filter(Company.company_id == actor.company_id)

    rows = query.all()
    return jsonify({"message": "companies found", "results": companies_schema.dump(rows)}), 200


@authenticate_return_auth
def company_get_by_id(req: Request, company_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(company_id):
        return jsonify({"message": "invalid company id"}), 404

    company = db.session.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return jsonify({"message": "company not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    return jsonify({"message": "company found", "results": company_schema.dump(company)}), 200


@authenticate_return_auth
def company_add(req: Request, auth_info) -> Response:
    if not is_enterprise_admin(auth_info.user):
        return jsonify({"message": "Only enterprise administrators can add companies"}), 403

    payload = req.get_json() or {}
    company = Company.blank(auth_info.user.enterprise_id)
    error = populate_object(company, payload)
    if error:
        return error

    company.phone = normalize_phone(company.phone)
    db.session.add(company)
    db.session.commit()
    ensure_company_task_statuses(company.company_id)
    return jsonify({"message": "company added", "results": company_schema.dump(company)}), 201


@authenticate_return_auth
def company_update(req: Request, company_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(company_id):
        return jsonify({"message": "invalid company id"}), 404

    company = db.session.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return jsonify({"message": "company not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not is_enterprise_admin(actor) and not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    error = populate_object(company, payload)
    if error:
        return error

    if hasattr(company, "phone"):
        company.phone = normalize_phone(company.phone)

    db.session.commit()
    return jsonify({"message": "company updated", "results": company_schema.dump(company)}), 200


@authenticate_return_auth
def company_set_active(req: Request, company_id, auth_info) -> Response:
    if not is_enterprise_admin(auth_info.user):
        return jsonify({"message": "Unauthorized"}), 403

    company = db.session.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return jsonify({"message": "company not found"}), 404

    payload = req.get_json() or {}
    company.active = bool(payload.get("active", True))
    db.session.commit()
    return jsonify({"message": "company status updated", "results": company_schema.dump(company)}), 200
