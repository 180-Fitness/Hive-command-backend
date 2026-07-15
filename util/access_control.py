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


def can_access_company(user, company_id):
    from util.user_companies import get_user_company_ids

    if is_enterprise_admin(user):
        return _company_in_enterprise(company_id, user.enterprise_id)
    return str(company_id) in get_user_company_ids(user)


def resolve_scope_company_id(req, actor):
    """Active company filter from X-Company-Id header or company_id query param."""
    from util.user_companies import get_user_company_ids
    from util.validate_uuid4 import validate_uuid4

    if not actor:
        return None

    raw = req.headers.get("X-Company-Id") or req.args.get("company_id")

    if is_enterprise_admin(actor):
        if not raw or not validate_uuid4(raw):
            return None
        if not _company_in_enterprise(raw, actor.enterprise_id):
            return None
        return str(raw)

    allowed = get_user_company_ids(actor)
    if raw and validate_uuid4(raw) and str(raw) in allowed:
        return str(raw)

    if str(actor.company_id) in allowed:
        return str(actor.company_id)

    return next(iter(allowed), None)


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
    from util.user_companies import get_user_company_ids

    if is_enterprise_admin(actor):
        return True
    if is_admin(actor):
        actor_companies = get_user_company_ids(actor)
        target_companies = get_user_company_ids(target)
        return bool(actor_companies & target_companies)
    return str(actor.user_id) == str(target.user_id)


def manageable_users_filter(query, actor):
    """Users an admin can manage — not limited to the active company switcher."""
    from sqlalchemy import or_

    from db import db
    from models.app_users import AppUser
    from models.user_companies_xref import user_companies
    from util.user_companies import get_user_company_ids

    if is_enterprise_admin(actor):
        return query.filter(AppUser.enterprise_id == actor.enterprise_id)

    allowed = list(get_user_company_ids(actor))
    if not allowed:
        return query.filter(AppUser.company_id == actor.company_id)

    return query.filter(
        or_(
            AppUser.company_id.in_(allowed),
            AppUser.user_id.in_(
                db.session.query(user_companies.c.user_id).filter(
                    user_companies.c.company_id.in_(allowed)
                )
            ),
        )
    )


def _enterprise_company_ids(enterprise_id):
    from db import db
    from models.companies import Company

    return db.session.query(Company.company_id).filter(
        Company.enterprise_id == enterprise_id,
        Company.active.is_(True),
    )


def company_scope_filter(query, model, user, scope_company_id=None):
    from sqlalchemy import or_

    from db import db
    from models.user_companies_xref import user_companies

    if scope_company_id:
        if getattr(model, "__tablename__", None) == "app_users":
            return query.filter(
                or_(
                    model.company_id == scope_company_id,
                    model.user_id.in_(
                        db.session.query(user_companies.c.user_id).filter(
                            user_companies.c.company_id == scope_company_id
                        )
                    ),
                )
            )
        return query.filter(model.company_id == scope_company_id)

    if is_enterprise_admin(user):
        if getattr(model, "__tablename__", None) == "app_users" and hasattr(
            model, "enterprise_id"
        ):
            return query.filter(model.enterprise_id == user.enterprise_id)
        return query.filter(
            model.company_id.in_(_enterprise_company_ids(user.enterprise_id))
        )

    from util.user_companies import get_user_company_ids

    allowed = list(get_user_company_ids(user))
    if not allowed:
        return query.filter(model.company_id == user.company_id)

    if getattr(model, "__tablename__", None) == "app_users":
        return query.filter(
            or_(
                model.company_id.in_(allowed),
                model.user_id.in_(
                    db.session.query(user_companies.c.user_id).filter(
                        user_companies.c.company_id.in_(allowed)
                    )
                ),
            )
        )

    return query.filter(model.company_id.in_(allowed))


def can_assign_role(actor, role, company_id=None):
    from util.user_companies import get_user_company_ids

    if role not in ASSIGNABLE_ROLES:
        return False
    if is_enterprise_admin(actor):
        return True
    if actor.role == COMPANY_ADMIN:
        if role == ENTERPRISE_ADMIN:
            return False
        if company_id is None:
            return True
        return str(company_id) in get_user_company_ids(actor)
    return False


def actor_can_assign_companies(actor, company_ids):
    from util.user_companies import get_user_company_ids

    if is_enterprise_admin(actor):
        return all(_company_in_enterprise(company_id, actor.enterprise_id) for company_id in company_ids)

    allowed = get_user_company_ids(actor)
    return all(str(company_id) in allowed for company_id in company_ids)


def company_admin_scope_company_id(actor, req):
    """Active company a company-admin may manage users for."""
    if is_enterprise_admin(actor) or actor.role != COMPANY_ADMIN:
        return None

    scope = resolve_scope_company_id(req, actor)
    if scope:
        return scope

    allowed = get_user_company_ids(actor)
    return next(iter(allowed), None)


def enforce_company_admin_company_ids(actor, req, company_ids):
    """Company admins may only assign users to their active company."""
    scope = company_admin_scope_company_id(actor, req)
    if not scope:
        return company_ids

    if company_ids and not all(str(company_id) == str(scope) for company_id in company_ids):
        return None

    return [scope]


def get_actor(auth_info):
    """Load the authenticated AppUser from an auth token record."""
    from sqlalchemy.orm import joinedload

    from db import db
    from models.app_users import AppUser

    if auth_info is None:
        return None

    if getattr(auth_info, "user_id", None):
        return (
            db.session.query(AppUser)
            .options(joinedload(AppUser.assigned_companies))
            .filter(AppUser.user_id == auth_info.user_id)
            .first()
        )

    return getattr(auth_info, "user", None)
