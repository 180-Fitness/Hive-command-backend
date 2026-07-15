import functools
from datetime import datetime, timezone

from flask import Response

from db import db
from models.app_users import AppUser
from models.auth_tokens import AuthTokens
from util.validate_uuid4 import validate_uuid4


def resolve_auth_token(request):
    token = request.headers.get("auth")

    if not token or not validate_uuid4(token):
        return None

    auth = (
        db.session.query(AuthTokens)
        .filter(AuthTokens.auth_token == token)
        .filter(AuthTokens.expiration > datetime.now(timezone.utc))
        .first()
    )
    if not auth:
        return None

    user_active = (
        db.session.query(AppUser.active)
        .filter(AppUser.user_id == auth.user_id)
        .scalar()
    )
    if not user_active:
        return None

    return auth


def unauthorized():
    return Response("Authentication Required", 401)


def authenticate(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if resolve_auth_token(args[0]):
            return func(*args, **kwargs)
        return unauthorized()

    return wrapper


def authenticate_return_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth_info = resolve_auth_token(args[0])
        if not auth_info:
            return unauthorized()
        kwargs["auth_info"] = auth_info
        return func(*args, **kwargs)

    return wrapper
