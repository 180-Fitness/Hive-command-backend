from sqlalchemy import inspect, text

from db import db


def ensure_notification_columns():
    inspector = inspect(db.engine)
    if "notifications" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("notifications")}
    statements = []

    if "company_id" not in existing:
        statements.append("ALTER TABLE notifications ADD COLUMN company_id UUID")
    if "calendar_event_id" not in existing:
        statements.append("ALTER TABLE notifications ADD COLUMN calendar_event_id UUID")
    if "notification_type" not in existing:
        statements.append(
            "ALTER TABLE notifications ADD COLUMN notification_type VARCHAR DEFAULT 'general'"
        )
    if "link" not in existing:
        statements.append(
            "ALTER TABLE notifications ADD COLUMN link VARCHAR DEFAULT '/calendar'"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
