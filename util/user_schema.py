from sqlalchemy import inspect, text

from db import db


def ensure_user_columns():
    inspector = inspect(db.engine)
    if "app_users" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("app_users")}
    statements = []

    if "job_title" not in existing:
        statements.append(
            "ALTER TABLE app_users ADD COLUMN job_title VARCHAR DEFAULT ''"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
