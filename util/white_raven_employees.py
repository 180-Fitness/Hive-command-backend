"""White Raven company employee roster."""

from util.access_control import COMPANY_ADMIN, MEMBER

COMPANY_NAME = "White Raven"
EMAIL_DOMAIN = "hive.com"
DEFAULT_PASSWORD = "Test123!"

# UI labels map to Hive Command roles: User -> member, Company Admin -> company-admin
ROLE_USER = MEMBER
ROLE_COMPANY_ADMIN = COMPANY_ADMIN

WHITE_RAVEN_EMPLOYEES = [
    {"first_name": "Martha", "last_name": "Whitman", "role": ROLE_USER},
    {"first_name": "Ashli", "last_name": "Broadhead", "role": ROLE_COMPANY_ADMIN},
    {"first_name": "Katie", "last_name": "Gleave", "role": ROLE_COMPANY_ADMIN},
    {"first_name": "Tori", "last_name": "Peckham", "role": ROLE_USER},
    {"first_name": "Halle", "last_name": "Cook", "role": ROLE_USER},
    {"first_name": "Shar", "last_name": "Hess", "role": ROLE_USER},
    {"first_name": "Lloyd", "last_name": "Gleave", "role": ROLE_COMPANY_ADMIN},
]


def employee_email(first_name):
    return f"{first_name.strip().lower()}@{EMAIL_DOMAIN}"


def employee_records():
    """Return full signup payloads (first/last name, email, password, role)."""
    return [
        {
            **employee,
            "email": employee_email(employee["first_name"]),
            "password": DEFAULT_PASSWORD,
        }
        for employee in WHITE_RAVEN_EMPLOYEES
    ]
