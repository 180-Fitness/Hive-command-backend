import os

import config
from db import db
from models.companies import Company


def _account_password(account):
    env_key = account.get("password_env")
    if env_key:
        return os.getenv(env_key, account.get("default_password", ""))
    return account.get("password", "")


def find_dashboard_account(username):
    if not username:
        return None

    normalized = username.strip().lower()
    for account in config.dashboard_accounts:
        if account.get("username", "").strip().lower() == normalized:
            return account
    return None


def verify_dashboard_credentials(username, password):
    account = find_dashboard_account(username)
    if not account or not password:
        return None

    expected = _account_password(account)
    if password != expected:
        return None

    company = (
        db.session.query(Company)
        .filter(Company.active.is_(True))
        .filter(Company.name == account["company_name"])
        .first()
    )
    if not company:
        return None

    return {
        "username": account["username"],
        "company": company,
    }
