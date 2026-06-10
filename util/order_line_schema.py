from sqlalchemy import inspect, text

from db import db


def ensure_order_lines_table():
    inspector = inspect(db.engine)
    if "order_lines" in inspector.get_table_names():
        return

    db.session.execute(
        text(
            """
            CREATE TABLE order_lines (
                order_line_id UUID PRIMARY KEY,
                company_id UUID NOT NULL REFERENCES companies(company_id),
                task_id UUID NOT NULL REFERENCES tasks(task_id),
                proofpix_order_number VARCHAR NOT NULL DEFAULT '',
                event_name VARCHAR NOT NULL DEFAULT '',
                bill_first_name VARCHAR NOT NULL DEFAULT '',
                bill_last_name VARCHAR NOT NULL DEFAULT '',
                student_name VARCHAR NOT NULL DEFAULT '',
                product_name VARCHAR NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 1,
                images VARCHAR NOT NULL DEFAULT '',
                ship_address1 VARCHAR NOT NULL DEFAULT '',
                ship_address2 VARCHAR NOT NULL DEFAULT '',
                ship_city VARCHAR NOT NULL DEFAULT '',
                ship_state VARCHAR NOT NULL DEFAULT '',
                ship_zip VARCHAR NOT NULL DEFAULT '',
                description VARCHAR NOT NULL DEFAULT '',
                active BOOLEAN NOT NULL DEFAULT TRUE,
                imported_at TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
    )
    db.session.execute(
        text(
            """
            CREATE UNIQUE INDEX uq_order_lines_dedup
            ON order_lines (task_id, proofpix_order_number, product_name, images)
            """
        )
    )
    db.session.commit()
