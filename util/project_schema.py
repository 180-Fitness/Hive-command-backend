from sqlalchemy import inspect, text

from db import db


def ensure_project_columns():
    inspector = inspect(db.engine)
    if "projects" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("projects")}
    statements = []

    if "user_deleted" not in existing:
        statements.append(
            "ALTER TABLE projects ADD COLUMN user_deleted BOOLEAN NOT NULL DEFAULT FALSE"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
