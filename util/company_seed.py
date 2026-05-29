from random import choice

import config
from db import db, query
from models.companies import Company
from models.task_statuses import TaskStatus


def ensure_company_task_statuses(company_id):
    if query(TaskStatus).filter(TaskStatus.company_id == company_id).first():
        return

    for index, status_name in enumerate(config.default_task_statuses):
        db.session.add(
            TaskStatus(
                company_id=company_id,
                name=status_name,
                color=choice(config.palette),
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
