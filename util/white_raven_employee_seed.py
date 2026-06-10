"""Create or sync White Raven employees from the roster."""

import config
from db import db
from models.app_users import AppUser
from models.companies import Company
from util.user_companies import set_user_company_assignments
from util.white_raven_employees import COMPANY_NAME, employee_records


def _resolve_company(company_name=COMPANY_NAME):
    company = (
        db.session.query(Company)
        .filter(Company.name == company_name)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        raise ValueError(f"Company not found: {company_name}")
    return company


def _sync_existing_user(user, record, company, reset_password, bcrypt):
    changed = False

    if not user.active:
        user.active = True
        changed = True

    if user.first_name != record["first_name"]:
        user.first_name = record["first_name"]
        changed = True

    if user.last_name != record["last_name"]:
        user.last_name = record["last_name"]
        changed = True

    if user.role != record["role"]:
        user.role = record["role"]
        changed = True

    if user.enterprise_id != company.enterprise_id:
        user.enterprise_id = company.enterprise_id
        changed = True

    company_ids = [str(company.company_id)]
    assigned_ids = {
        str(company_ref.company_id) for company_ref in (user.assigned_companies or [])
    }
    if str(user.company_id) != company_ids[0] or assigned_ids != {company_ids[0]}:
        changed = True

    if changed or not user.assigned_companies:
        set_user_company_assignments(user, company_ids)

    if reset_password:
        user.password = bcrypt.generate_password_hash(record["password"]).decode("utf-8")
        changed = True

    return changed


def seed_white_raven_employees(company_name=COMPANY_NAME, reset_password=False):
    from app import bcrypt

    company = _resolve_company(company_name)
    company_id = str(company.company_id)
    created = []
    updated = []
    skipped = []

    for index, record in enumerate(employee_records()):
        email = record["email"]
        existing = db.session.query(AppUser).filter(AppUser.email == email).first()

        if existing:
            if _sync_existing_user(existing, record, company, reset_password, bcrypt):
                updated.append(email)
            else:
                skipped.append(email)
            continue

        user = AppUser(
            enterprise_id=company.enterprise_id,
            company_id=company.company_id,
            first_name=record["first_name"],
            last_name=record["last_name"],
            email=email,
            password=bcrypt.generate_password_hash(record["password"]).decode("utf-8"),
            role=record["role"],
            color=config.palette[index % len(config.palette)],
        )
        db.session.add(user)
        db.session.flush()
        set_user_company_assignments(user, [company_id])
        created.append(email)

    db.session.commit()

    return {
        "company_id": company_id,
        "company_name": company.name,
        "created_count": len(created),
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }
