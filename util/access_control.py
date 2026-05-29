ENTERPRISE_ADMIN = "enterprise-admin"
COMPANY_ADMIN = "company-admin"
MEMBER = "member"

ADMIN_ROLES = (ENTERPRISE_ADMIN, COMPANY_ADMIN)
ASSIGNABLE_ROLES = (MEMBER, COMPANY_ADMIN, ENTERPRISE_ADMIN)


def is_enterprise_admin(user):
    return user.role == ENTERPRISE_ADMIN


def is_admin(user):
    return user.role in ADMIN_ROLES


def is_member(user):
    return user.role == MEMBER


def can_access_company(user, company_id):
    if is_enterprise_admin(user):
        return True
    return str(user.company_id) == str(company_id)


def _company_in_enterprise(company_id, enterprise_id):
    from db import db
    from models.companies import Company

    company = (
        db.session.query(Company)
        .filter(Company.company_id == company_id)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        return False
    return str(company.enterprise_id) == str(enterprise_id)


def resolve_scope_company_id(req, actor):
    """Active company filter from X-Company-Id header or company_id query param."""
    if not actor:
        return None

    if not is_enterprise_admin(actor):
        return str(actor.company_id)

    from util.validate_uuid4 import validate_uuid4

    raw = req.headers.get("X-Company-Id") or req.args.get("company_id")
    if not raw or not validate_uuid4(raw):
        return None

    if not _company_in_enterprise(raw, actor.enterprise_id):
        return None

    return str(raw)


def effective_company_id(req, actor, payload=None):
    """Default company_id for creates when payload omits it."""
    payload = payload or {}
    if payload.get("company_id"):
        return payload.get("company_id")

    scope = resolve_scope_company_id(req, actor)
    if scope:
        return scope

    return actor.company_id


def can_access_company_scoped(user, company_id, scope_company_id=None):
    if scope_company_id and str(company_id) != str(scope_company_id):
        return False
    return can_access_company(user, company_id)


def can_manage_user(actor, target):
    if is_enterprise_admin(actor):
        return True
    if is_admin(actor) and str(actor.company_id) == str(target.company_id):
        return True
    return str(actor.user_id) == str(target.user_id)


def company_scope_filter(query, model, user, scope_company_id=None):
    if scope_company_id:
        return query.filter(model.company_id == scope_company_id)
    if is_enterprise_admin(user):
        return query
    return query.filter(model.company_id == user.company_id)


def can_assign_role(actor, role, company_id=None):
    if role not in ASSIGNABLE_ROLES:
        return False
    if is_enterprise_admin(actor):
        return True
    if actor.role == COMPANY_ADMIN:
        if role == ENTERPRISE_ADMIN:
            return False
        return company_id is None or str(actor.company_id) == str(company_id)
    return False


def get_actor(auth_info):
    """Load the authenticated AppUser from an auth token record."""
    from db import db
    from models.app_users import AppUser

    if auth_info is None:
        return None

    if getattr(auth_info, "user_id", None):
        return db.session.query(AppUser).filter(AppUser.user_id == auth_info.user_id).first()

    return getattr(auth_info, "user", None)
