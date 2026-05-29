from db import db
from models.companies import Company
from util.validate_uuid4 import validate_uuid4


def get_user_company_ids(user):
    if user is None:
        return set()

    ids = {str(company.company_id) for company in (user.assigned_companies or [])}
    if user.company_id:
        ids.add(str(user.company_id))
    return ids


def normalize_company_ids(raw_ids):
    if not raw_ids:
        return []

    seen = []
    for company_id in raw_ids:
        if not company_id or not validate_uuid4(str(company_id)):
            continue
        value = str(company_id)
        if value not in seen:
            seen.append(value)
    return seen


def load_companies_for_assignment(enterprise_id, company_ids):
    if not company_ids:
        return []

    return (
        db.session.query(Company)
        .filter(Company.enterprise_id == enterprise_id)
        .filter(Company.active.is_(True))
        .filter(Company.company_id.in_(company_ids))
        .all()
    )


def set_user_company_assignments(user, company_ids):
    companies = load_companies_for_assignment(user.enterprise_id, company_ids)
    if len(companies) != len(company_ids):
        return False

    ordered = []
    for company_id in company_ids:
        match = next((c for c in companies if str(c.company_id) == str(company_id)), None)
        if match:
            ordered.append(match)

    user.assigned_companies = ordered
    user.company_id = ordered[0].company_id
    return True


def backfill_user_company_assignments():
    from sqlalchemy.orm import joinedload

    from models.app_users import AppUser

    updated = False
    for user in db.session.query(AppUser).options(joinedload(AppUser.assigned_companies)).all():
        if user.assigned_companies:
            continue
        company = (
            db.session.query(Company)
            .filter(Company.company_id == user.company_id)
            .first()
        )
        if company:
            user.assigned_companies = [company]
            updated = True

    if updated:
        db.session.commit()
