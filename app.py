import os
import re
from random import choice

from dotenv import load_dotenv
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate

import config
from db import db, init_db, query
from models.app_users import AppUser
from models.companies import Company
from models.enterprise import Enterprise
from models.task_statuses import TaskStatus
from util.access_control import ENTERPRISE_ADMIN
from util.blueprints import register_blueprints
from util.calendar_schema import ensure_calendar_event_columns
from util.user_schema import ensure_user_columns
from util.notification_schema import ensure_notification_columns
from util.task_schema import ensure_task_due_date_column
from util.project_schema import ensure_project_columns
from util.company_seed import ensure_company_task_statuses, seed_hive_group_companies
from util.user_companies import backfill_user_company_assignments

load_dotenv()


def _normalize_database_url(url):
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _database_uri():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return _normalize_database_url(database_url)

    host = os.getenv("DATABASE_HOST", "127.0.0.1")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", config.database_name)
    user = os.getenv("DATABASE_USER") or os.getenv("USER", "postgres")
    password = os.getenv("DATABASE_PASS", "")

    if password:
        credentials = f"{user}:{password}"
    else:
        credentials = user

    return f"postgresql+psycopg2://{credentials}@{host}:{port}/{name}"


def _cors_origins():
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    for url in os.getenv("FRONTEND_URL", "").split(","):
        url = url.strip().rstrip("/")
        if url and url not in origins:
            origins.append(url)
    # Private LAN origins for phone / local network testing
    if os.getenv("ALLOW_LAN_CORS", "1").lower() in ("1", "true", "yes"):
        origins.extend(
            [
                re.compile(
                    r"^https?://("
                    r"localhost|127\.0\.0\.1|"
                    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
                    r"192\.168\.\d{1,3}\.\d{1,3}|"
                    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
                    r")(:\d+)?$"
                )
            ]
        )
    return origins


def seed_bootstrap_data(bcrypt):
    enterprise = query(Enterprise).first()
    if not enterprise:
        enterprise = Enterprise(
            name=config.enterprise_name,
            email=config.enterprise_email,
            phone=config.enterprise_phone,
        )
        db.session.add(enterprise)
        db.session.commit()
    elif enterprise.name != config.enterprise_name:
        enterprise.name = config.enterprise_name
        db.session.commit()

    company = (
        query(Company)
        .filter(Company.enterprise_id == enterprise.enterprise_id)
        .filter(Company.name == config.default_company_name)
        .first()
    )
    if not company:
        company = Company(
            enterprise_id=enterprise.enterprise_id,
            name=config.default_company_name,
            email=config.enterprise_email,
            phone=config.enterprise_phone,
            city=config.default_company_city,
            state=config.default_company_state,
            postal=config.default_company_postal,
            color=choice(config.palette),
            code="HQ",
        )
        db.session.add(company)
        db.session.commit()

    if not query(TaskStatus).filter(TaskStatus.company_id == company.company_id).first():
        ensure_company_task_statuses(company.company_id)

    seed_hive_group_companies(enterprise.enterprise_id)
    backfill_user_company_assignments()

    admin = query(AppUser).filter(AppUser.email == config.admin_email).first()
    if not admin:
        password = os.getenv("HIVE_ADMIN_PASSWORD", "")
        if not password:
            raise RuntimeError(
                "HIVE_ADMIN_PASSWORD must be set in the environment before first deploy."
            )

        admin = AppUser(
            enterprise_id=enterprise.enterprise_id,
            company_id=company.company_id,
            first_name=config.admin_first_name,
            last_name=config.admin_last_name,
            email=config.admin_email,
            phone=config.admin_phone,
            password=bcrypt.generate_password_hash(password).decode("utf-8"),
            role=ENTERPRISE_ADMIN,
            color=choice(config.palette),
        )
        db.session.add(admin)
        db.session.commit()


def create_all(bcrypt):
    with app.app_context():
        db.create_all()
        ensure_user_columns()
        ensure_calendar_event_columns()
        ensure_notification_columns()
        ensure_task_due_date_column()
        ensure_project_columns()
        seed_bootstrap_data(bcrypt)


def create_app():
    application = Flask(__name__)
    application.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    init_db(application, db)
    migrate.init_app(application, db)
    return application


migrate = Migrate()
app = create_app()
bcrypt = Bcrypt(app)
CORS(
    app,
    origins=_cors_origins(),
    supports_credentials=True,
    allow_headers=["Content-Type", "auth", "dashboard-auth", "X-Company-Id"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
Marshmallow(app)
register_blueprints(app)

# Upload size cap (Numbers calendar sync and any future uploads)
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_BYTES", 15 * 1024 * 1024))


@app.after_request
def set_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
    )
    if os.getenv("ENABLE_HSTS", "").lower() in ("1", "true", "yes"):
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


if __name__ == "__main__":
    create_all(bcrypt)
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=os.getenv("PORT", "8090"),
        debug=os.getenv("FLASK_DEBUG", "0") in ("1", "true", "yes"),
    )
