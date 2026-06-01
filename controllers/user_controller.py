from flask import Request, Response, jsonify
from flask_bcrypt import check_password_hash, generate_password_hash
from sqlalchemy.orm import joinedload

from db import db
from lib.authenticate import authenticate_return_auth
from models.app_users import (
    AppUser,
    assignees_schema,
    user_schema,
    users_schema,
)
from util.access_control import (
    MEMBER,
    actor_can_assign_companies,
    can_access_company,
    can_assign_role,
    can_manage_user,
    company_scope_filter,
    effective_company_id,
    is_admin,
    is_enterprise_admin,
    is_member,
    manageable_users_filter,
    resolve_scope_company_id,
)
from util.phone import normalize_phone
from util.reflection import populate_object
from util.user_companies import normalize_company_ids, set_user_company_assignments
from util.validate_password import validate_password
from util.validate_uuid4 import validate_uuid4


def _forbidden():
    return jsonify({"message": "Forbidden"}), 403


def _actor(req_auth):
    return (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == req_auth.user_id)
        .first()
    )


def _parse_company_ids(payload, actor, req):
    raw = payload.get("company_ids")
    if raw is not None:
        company_ids = normalize_company_ids(raw if isinstance(raw, list) else [raw])
    elif payload.get("company_id"):
        company_ids = normalize_company_ids([payload.get("company_id")])
    else:
        company_ids = normalize_company_ids([effective_company_id(req, actor, payload)])

    return company_ids


@authenticate_return_auth
def users_get_all(req: Request, auth_info) -> Response:
    actor = _actor(auth_info)
    if not is_admin(actor):
        return _forbidden()

    query = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .order_by(AppUser.last_name.asc(), AppUser.first_name.asc())
    )
    query = manageable_users_filter(query, actor)
    return jsonify({"message": "users found", "results": users_schema.dump(query.all())}), 200


@authenticate_return_auth
def users_assignees_get(req: Request, auth_info) -> Response:
    actor = _actor(auth_info)
    query = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.active.is_(True))
        .order_by(AppUser.last_name.asc(), AppUser.first_name.asc())
    )
    scope = resolve_scope_company_id(req, actor)
    query = company_scope_filter(query, AppUser, actor, scope)
    return jsonify({"message": "assignees found", "results": assignees_schema.dump(query.all())}), 200


@authenticate_return_auth
def user_get_by_id(req: Request, user_id, auth_info) -> Response:
    if not validate_uuid4(user_id):
        return jsonify({"message": "invalid user id"}), 404

    actor = _actor(auth_info)
    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == user_id)
        .first()
    )
    if not user:
        return jsonify({"message": "user not found"}), 404

    if not can_manage_user(actor, user) and not is_admin(actor):
        return _forbidden()

    if is_member(actor) and str(actor.user_id) != user_id:
        return _forbidden()

    return jsonify({"message": "user found", "results": user_schema.dump(user)}), 200


@authenticate_return_auth
def user_get_me(req: Request, auth_info) -> Response:
    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == auth_info.user_id)
        .first()
    )
    return jsonify({"message": "user found", "results": user_schema.dump(user)}), 200


@authenticate_return_auth
def users_get_by_company(req: Request, company_id, auth_info) -> Response:
    actor = _actor(auth_info)
    if not is_admin(actor):
        return _forbidden()

    if not validate_uuid4(company_id) or not can_access_company(actor, company_id):
        return _forbidden()

    query = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.company_id == company_id)
    )
    scope = resolve_scope_company_id(req, actor)
    query = company_scope_filter(query, AppUser, actor, scope)
    return jsonify({"message": "users found", "results": users_schema.dump(query.all())}), 200


@authenticate_return_auth
def user_add(req: Request, auth_info) -> Response:
    actor = _actor(auth_info)
    if not is_admin(actor):
        return _forbidden()

    payload = req.get_json() or {}
    password = payload.get("password")
    email = (payload.get("email") or "").strip().lower()
    first_name = (payload.get("first_name") or "").strip()
    last_name = (payload.get("last_name") or "").strip()

    if not email or not first_name or not last_name:
        return jsonify({"message": "First name, last name, and email are required"}), 400

    if not validate_password(password):
        return jsonify({"message": "Password does not meet requirements"}), 400

    if db.session.query(AppUser).filter(AppUser.email == email).first():
        return jsonify({"message": "A user with that email already exists"}), 409

    company_ids = _parse_company_ids(payload, actor, req)
    if not company_ids:
        return jsonify({"message": "At least one company is required"}), 400

    if not actor_can_assign_companies(actor, company_ids):
        return _forbidden()

    role = payload.get("role", MEMBER)
    if not can_assign_role(actor, role, company_ids[0]):
        return jsonify({"message": "Unauthorized role assignment"}), 403

    user = AppUser(
        enterprise_id=actor.enterprise_id,
        company_id=company_ids[0],
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=generate_password_hash(password).decode("utf-8"),
        phone=normalize_phone(payload.get("phone", "")),
        role=role,
        color=payload.get("color", "#2563EB"),
    )
    db.session.add(user)
    db.session.flush()

    if not set_user_company_assignments(user, company_ids):
        db.session.rollback()
        return jsonify({"message": "Invalid company selection"}), 400

    db.session.commit()
    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == user.user_id)
        .first()
    )
    return jsonify({"message": "user added", "results": user_schema.dump(user)}), 201


@authenticate_return_auth
def user_update(req: Request, user_id, auth_info) -> Response:
    if not validate_uuid4(user_id):
        return jsonify({"message": "invalid user id"}), 404

    actor = _actor(auth_info)
    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == user_id)
        .first()
    )
    if not user:
        return jsonify({"message": "user not found"}), 404

    is_self = str(actor.user_id) == user_id
    if not is_self and not can_manage_user(actor, user):
        return _forbidden()

    payload = dict(req.get_json() or {})

    if is_member(actor):
        payload.pop("role", None)
        payload.pop("company_id", None)
        payload.pop("company_ids", None)
        payload.pop("active", None)
        if not is_self:
            return _forbidden()

    company_ids = None
    if "company_ids" in payload:
        if not is_admin(actor):
            payload.pop("company_ids", None)
        else:
            company_ids = normalize_company_ids(payload.pop("company_ids") or [])
            if not company_ids:
                return jsonify({"message": "At least one company is required"}), 400
            if not actor_can_assign_companies(actor, company_ids):
                return _forbidden()

    if "role" in payload and not can_assign_role(actor, payload["role"], user.company_id):
        return jsonify({"message": "Unauthorized role assignment"}), 403

    if "company_id" in payload and not is_enterprise_admin(actor):
        payload.pop("company_id", None)

    if "password" in payload:
        if not validate_password(payload["password"]):
            return jsonify({"message": "Password does not meet requirements"}), 400
        payload["password"] = generate_password_hash(payload["password"]).decode("utf-8")

    if "email" in payload:
        email = payload["email"].strip().lower()
        existing = db.session.query(AppUser).filter(AppUser.email == email).first()
        if existing and str(existing.user_id) != user_id:
            return jsonify({"message": "A user with that email already exists"}), 409
        payload["email"] = email

    error = populate_object(user, payload)
    if error:
        return error

    if "phone" in payload:
        user.phone = normalize_phone(user.phone)

    if company_ids is not None and not set_user_company_assignments(user, company_ids):
        return jsonify({"message": "Invalid company selection"}), 400

    db.session.commit()
    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == user.user_id)
        .first()
    )
    return jsonify({"message": "user updated", "results": user_schema.dump(user)}), 200


@authenticate_return_auth
def user_set_active(req: Request, user_id, auth_info) -> Response:
    actor = _actor(auth_info)
    if not is_admin(actor):
        return _forbidden()

    if not validate_uuid4(user_id):
        return jsonify({"message": "invalid user id"}), 404

    user = db.session.query(AppUser).filter(AppUser.user_id == user_id).first()
    if not user:
        return jsonify({"message": "user not found"}), 404

    if not can_manage_user(actor, user):
        return _forbidden()

    if str(actor.user_id) == user_id:
        return jsonify({"message": "You cannot deactivate your own account"}), 400

    payload = req.get_json() or {}
    user.active = bool(payload.get("active", True))
    db.session.commit()
    return jsonify({"message": "user status updated", "results": user_schema.dump(user)}), 200


@authenticate_return_auth
def user_verify_password(req: Request, auth_info) -> Response:
    payload = req.get_json() or {}
    password = payload.get("password")
    user = db.session.query(AppUser).filter(AppUser.user_id == auth_info.user_id).first()

    if user and check_password_hash(user.password, password):
        return jsonify({"message": "Password verified"}), 200

    return jsonify({"message": "Invalid password"}), 401
