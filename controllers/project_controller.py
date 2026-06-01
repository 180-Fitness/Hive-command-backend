from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.projects import Project, project_schema, projects_schema
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
def projects_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    query = db.session.query(Project).filter(Project.active.is_(True)).order_by(Project.name.asc())
    query = company_scope_filter(query, Project, actor, scope)
    return jsonify({"message": "projects found", "results": projects_schema.dump(query.all())}), 200


@authenticate_return_auth
def project_get_by_id(req: Request, project_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(project_id):
        return jsonify({"message": "invalid project id"}), 404

    project = db.session.query(Project).filter(Project.project_id == project_id).first()
    if not project or not project.active:
        return jsonify({"message": "project not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, project.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    return jsonify({"message": "project found", "results": project_schema.dump(project)}), 200


@authenticate_return_auth
def project_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    payload = req.get_json() or {}
    company_id = effective_company_id(req, actor, payload)

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    project = Project(
        company_id=company_id,
        name=payload.get("name", ""),
        created_by_id=actor.user_id,
        color=payload.get("color", "#2563EB"),
        description=payload.get("description", ""),
        client_id=payload.get("client_id"),
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({"message": "project added", "results": project_schema.dump(project)}), 201


@authenticate_return_auth
def project_update(req: Request, project_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(project_id):
        return jsonify({"message": "invalid project id"}), 404

    project = db.session.query(Project).filter(Project.project_id == project_id).first()
    if not project or not project.active:
        return jsonify({"message": "project not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, project.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    error = populate_object(project, req.get_json() or {})
    if error:
        return error

    db.session.commit()
    return jsonify({"message": "project updated", "results": project_schema.dump(project)}), 200


@authenticate_return_auth
def project_delete(req: Request, project_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(project_id):
        return jsonify({"message": "invalid project id"}), 404

    project = db.session.query(Project).filter(Project.project_id == project_id).first()
    if not project or not project.active:
        return jsonify({"message": "project not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, project.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    project.active = False
    db.session.commit()
    return jsonify({"message": "project deleted"}), 200
