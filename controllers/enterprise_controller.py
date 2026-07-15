from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.app_users import AppUser
from models.enterprise import Enterprise, enterprise_schema


@authenticate_return_auth
def enterprise_get(req: Request, auth_info) -> Response:
    from util.access_control import is_admin

    actor = db.session.query(AppUser).filter(AppUser.user_id == auth_info.user_id).first()
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    enterprise = (
        db.session.query(Enterprise)
        .filter(Enterprise.enterprise_id == actor.enterprise_id)
        .first()
    )
    if not enterprise:
        return jsonify({"message": "Enterprise not configured"}), 404
    return jsonify({"message": "enterprise found", "results": enterprise_schema.dump(enterprise)}), 200
