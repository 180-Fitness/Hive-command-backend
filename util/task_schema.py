from sqlalchemy import inspect, text

from db import db


def ensure_task_due_date_column():
    inspector = inspect(db.engine)
    if "tasks" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("tasks")}
    statements = []

    if "due_date" not in existing:
        statements.append("ALTER TABLE tasks ADD COLUMN due_date DATE")

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
