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

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
