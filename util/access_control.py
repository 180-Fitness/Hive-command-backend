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


def can_manage_user(actor, target):
    if is_enterprise_admin(actor):
        return True
    if is_admin(actor) and str(actor.company_id) == str(target.company_id):
        return True
    return str(actor.user_id) == str(target.user_id)


def company_scope_filter(query, model, user):
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
