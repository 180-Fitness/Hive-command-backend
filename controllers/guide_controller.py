from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.guides import Guide, guide_schema, guides_schema
from util.access_control import (
    can_access_company_scoped,
    company_scope_filter,
    effective_company_id,
    get_actor,
    is_admin,
    resolve_scope_company_id,
)
from util.reflection import populate_object
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def guides_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    query = (
        db.session.query(Guide)
        .filter(Guide.active.is_(True))
        .order_by(Guide.sort_order.asc(), Guide.title.asc())
    )
    query = company_scope_filter(query, Guide, actor, scope)
    return jsonify({"message": "guides found", "results": guides_schema.dump(query.all())}), 200


@authenticate_return_auth
def guides_admin_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    scope = resolve_scope_company_id(req, actor)
    query = db.session.query(Guide).order_by(Guide.sort_order.asc(), Guide.title.asc())
    query = company_scope_filter(query, Guide, actor, scope)
    return jsonify({"message": "guides found", "results": guides_schema.dump(query.all())}), 200


@authenticate_return_auth
def guide_get_by_id(req: Request, guide_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(guide_id):
        return jsonify({"message": "invalid guide id"}), 404

    guide = db.session.query(Guide).filter(Guide.guide_id == guide_id).first()
    if not guide:
        return jsonify({"message": "guide not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, guide.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    if not guide.active and not is_admin(actor):
        return jsonify({"message": "guide not found"}), 404

    return jsonify({"message": "guide found", "results": guide_schema.dump(guide)}), 200


@authenticate_return_auth
def guide_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"message": "Title is required"}), 400

    company_id = effective_company_id(req, actor, payload)
    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    guide = Guide(
        company_id=company_id,
        title=title,
        created_by_id=actor.user_id,
        summary=(payload.get("summary") or "").strip(),
        body=(payload.get("body") or "").strip(),
        sort_order=payload.get("sort_order", 0),
    )
    db.session.add(guide)
    db.session.commit()
    return jsonify({"message": "guide added", "results": guide_schema.dump(guide)}), 201


@authenticate_return_auth
def guide_update(req: Request, guide_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(guide_id):
        return jsonify({"message": "invalid guide id"}), 404

    guide = db.session.query(Guide).filter(Guide.guide_id == guide_id).first()
    if not guide:
        return jsonify({"message": "guide not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, guide.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    if "title" in payload and not str(payload.get("title", "")).strip():
        return jsonify({"message": "Title is required"}), 400

    error = populate_object(guide, payload)
    if error:
        return error

    if "title" in payload:
        guide.title = guide.title.strip()
    if "summary" in payload:
        guide.summary = (guide.summary or "").strip()
    if "body" in payload:
        guide.body = (guide.body or "").strip()

    db.session.commit()
    return jsonify({"message": "guide updated", "results": guide_schema.dump(guide)}), 200


@authenticate_return_auth
def guide_delete(req: Request, guide_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(guide_id):
        return jsonify({"message": "invalid guide id"}), 404

    guide = db.session.query(Guide).filter(Guide.guide_id == guide_id).first()
    if not guide:
        return jsonify({"message": "guide not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, guide.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    guide.active = False
    db.session.commit()
    return jsonify({"message": "guide removed"}), 200
