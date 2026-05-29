from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate, authenticate_return_auth
from models.app_users import AppUser
from models.companies import Company, company_schema, companies_schema
from util.access_control import can_access_company, company_scope_filter, is_enterprise_admin
from util.phone import normalize_phone
from util.reflection import populate_object
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def companies_get(req: Request, auth_info) -> Response:
    actor = db.session.query(AppUser).filter(AppUser.user_id == auth_info.user_id).first()
    if not is_enterprise_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    query = db.session.query(Company).filter(Company.active.is_(True)).order_by(Company.name.asc())
    query = company_scope_filter(query, Company, actor)
    rows = query.all()
    return jsonify({"message": "companies found", "results": companies_schema.dump(rows)}), 200


@authenticate_return_auth
def company_get_by_id(req: Request, company_id, auth_info) -> Response:
    if not validate_uuid4(company_id):
        return jsonify({"message": "invalid company id"}), 404

    company = db.session.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return jsonify({"message": "company not found"}), 404

    if not can_access_company(auth_info.user, company_id):
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
    return jsonify({"message": "company added", "results": company_schema.dump(company)}), 201


@authenticate_return_auth
def company_update(req: Request, company_id, auth_info) -> Response:
    if not validate_uuid4(company_id):
        return jsonify({"message": "invalid company id"}), 404

    company = db.session.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return jsonify({"message": "company not found"}), 404

    if not is_enterprise_admin(auth_info.user) and not can_access_company(auth_info.user, company_id):
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
