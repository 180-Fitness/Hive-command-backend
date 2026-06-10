from random import choice

import config
from db import db, query
from models.companies import Company
from models.task_statuses import TaskStatus
from util.company_workflow import sync_company_task_statuses, task_status_defs_for_company


def ensure_company_task_statuses(company_id):
    company = query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return

    if company.name in config.company_task_statuses:
        sync_company_task_statuses(company)
        return

    if query(TaskStatus).filter(TaskStatus.company_id == company_id).first():
        return

    defs = task_status_defs_for_company(company)
    for index, defn in enumerate(defs):
        name = defn["name"] if isinstance(defn, dict) else defn
        color = defn.get("color", choice(config.palette)) if isinstance(defn, dict) else choice(config.palette)
        db.session.add(
            TaskStatus(
                company_id=company_id,
                name=name,
                color=color,
                is_default=index == 0,
                sort_order=index,
            )
        )
    db.session.commit()


def seed_hive_group_companies(enterprise_id):
    """Create any missing Hive Group subsidiaries and their workflow statuses."""
    for entry in config.hive_group_companies:
        company = (
            query(Company)
            .filter(Company.enterprise_id == enterprise_id)
            .filter(Company.name == entry["name"])
            .first()
        )
        if not company:
            company = Company(
                enterprise_id=enterprise_id,
                name=entry["name"],
                code=entry.get("code"),
                color=entry.get("color", choice(config.palette)),
                email=config.enterprise_email,
                phone=config.enterprise_phone,
            )
            db.session.add(company)
            db.session.commit()

        ensure_company_task_statuses(company.company_id)
