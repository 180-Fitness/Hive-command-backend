import os
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

load_dotenv()


def _database_uri():
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
        for index, status_name in enumerate(config.default_task_statuses):
            db.session.add(
                TaskStatus(
                    company_id=company.company_id,
                    name=status_name,
                    color=choice(config.palette),
                    is_default=index == 0,
                    sort_order=index,
                )
            )
        db.session.commit()

    admin = query(AppUser).filter(AppUser.email == config.admin_email).first()
    if not admin:
        password = os.getenv("HIVE_ADMIN_PASSWORD", "")
        if not password:
            password = input(f"Enter a password for {config.admin_email}: ")

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
    origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    supports_credentials=True,
    allow_headers=["Content-Type", "auth"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
Marshmallow(app)
register_blueprints(app)


if __name__ == "__main__":
    create_all(bcrypt)
    app.run(port=os.getenv("PORT", "8090"), debug=True)
