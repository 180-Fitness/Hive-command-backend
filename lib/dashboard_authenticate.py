import functools
from datetime import datetime, timezone

from flask import Response

from db import db
from models.companies import Company
from models.dashboard_auth_tokens import DashboardAuthTokens
from util.validate_uuid4 import validate_uuid4


def resolve_dashboard_auth_token(request):
    token = request.headers.get("dashboard-auth")

    if not token or not validate_uuid4(token):
        return None

    auth = (
        db.session.query(DashboardAuthTokens)
        .filter(DashboardAuthTokens.auth_token == token)
        .filter(DashboardAuthTokens.expiration > datetime.now(timezone.utc))
        .first()
    )
    if not auth:
        return None

    company_active = (
        db.session.query(Company.active)
        .filter(Company.company_id == auth.company_id)
        .scalar()
    )
    if not company_active:
        return None

    return auth


def unauthorized():
    return Response("Dashboard Authentication Required", 401)


def dashboard_authenticate_return_auth(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth_info = resolve_dashboard_auth_token(args[0])
        if not auth_info:
            return unauthorized()
        kwargs["auth_info"] = auth_info
        return func(*args, **kwargs)

    return wrapper
