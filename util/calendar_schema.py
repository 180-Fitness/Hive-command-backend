from sqlalchemy import inspect, text

from db import db


def ensure_calendar_event_columns():
    inspector = inspect(db.engine)
    if "calendar_events" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("calendar_events")}
    statements = []

    if "school" not in existing:
        statements.append(
            "ALTER TABLE calendar_events ADD COLUMN school VARCHAR DEFAULT ''"
        )
    if "event_type" not in existing:
        statements.append(
            "ALTER TABLE calendar_events ADD COLUMN event_type VARCHAR DEFAULT ''"
        )
    if "num_stations" not in existing:
        statements.append(
            "ALTER TABLE calendar_events ADD COLUMN num_stations INTEGER"
        )
    if "num_students" not in existing:
        statements.append(
            "ALTER TABLE calendar_events ADD COLUMN num_students INTEGER"
        )
    if "location" not in existing:
        statements.append(
            "ALTER TABLE calendar_events ADD COLUMN location VARCHAR DEFAULT ''"
        )
    # sh/shoot-day-sms-reminders
    # if "contact_phone" not in existing:
    #     statements.append(
    #         "ALTER TABLE calendar_events ADD COLUMN contact_phone VARCHAR DEFAULT ''"
    #     )
    # if "shoot_reminder_sms_sent_at" not in existing:
    #     statements.append(
    #         "ALTER TABLE calendar_events ADD COLUMN shoot_reminder_sms_sent_at TIMESTAMP"
    #     )
    if "project_id" not in existing:
        statements.append(
            "ALTER TABLE calendar_events ADD COLUMN project_id UUID "
            "REFERENCES projects(project_id)"
        )

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
