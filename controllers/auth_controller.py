import os
from datetime import datetime, timedelta, timezone

from flask import Request, Response, jsonify
from flask_bcrypt import check_password_hash

from sqlalchemy.orm import joinedload

import config
from db import db
from lib.authenticate import authenticate_return_auth
from models.app_users import AppUser, user_schema
from models.auth_tokens import AuthTokens, auth_token_schema


def auth_token_add(req: Request) -> Response:
    if req.content_type != "application/json":
        return jsonify({"message": "Request must be JSON"}), 400

    payload = req.get_json() or {}
    email = payload.get("email")
    password = payload.get("password")

    if not email or not password:
        return jsonify({"message": "Invalid login"}), 401

    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.email == email)
        .filter(AppUser.active.is_(True))
        .first()
    )

    if not user or not check_password_hash(user.password, password):
        return jsonify({"message": "Invalid email or password"}), 401

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=12)

    if config.purge_expired_auth_tokens:
        expired = (
            db.session.query(AuthTokens)
            .filter(AuthTokens.user_id == user.user_id)
            .filter(AuthTokens.expiration < now)
            .all()
        )
        for token in expired:
            db.session.delete(token)

    session = AuthTokens(user.user_id, expires)
    db.session.add(session)
    db.session.commit()

    return jsonify(
        {
            "message": "Auth success",
            "results": {
                "auth_info": auth_token_schema.dump(session),
                "user_info": user_schema.dump(user),
            },
        }
    )


@authenticate_return_auth
def auth_token_remove(req: Request, auth_info) -> Response:
    db.session.delete(auth_info)
    db.session.commit()
    return jsonify({"message": "User logged out"}), 200


@authenticate_return_auth
def auth_check_login(req: Request, auth_info) -> Response:
    user = (
        db.session.query(AppUser)
        .options(joinedload(AppUser.assigned_companies))
        .filter(AppUser.user_id == auth_info.user_id)
        .first()
    )
    return jsonify(
        {
            "message": "success",
            "results": {
                "auth_info": auth_token_schema.dump(auth_info),
                "user_info": user_schema.dump(user),
            },
        }
    ), 200


@authenticate_return_auth
def auth_token_remove_expired(req: Request, auth_info) -> Response:
    from util.access_control import is_enterprise_admin

    user = db.session.query(AppUser).filter(AppUser.user_id == auth_info.user_id).first()
    if not user or not is_enterprise_admin(user):
        return jsonify({"message": "Unauthorized"}), 403

    now = datetime.now(timezone.utc)
    expired = db.session.query(AuthTokens).filter(AuthTokens.expiration < now).all()
    for token in expired:
        db.session.delete(token)
    db.session.commit()
    return jsonify({"message": "Expired auth tokens removed"}), 200
