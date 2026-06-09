import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class OrderLine(db.Model):
    __tablename__ = "order_lines"
    __table_args__ = (
        db.UniqueConstraint(
            "task_id",
            "proofpix_order_number",
            "product_name",
            "images",
            name="uq_order_lines_dedup",
        ),
    )

    order_line_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tasks.task_id"), nullable=False)
    proofpix_order_number = db.Column(db.String(), nullable=False, default="")
    event_name = db.Column(db.String(), nullable=False, default="")
    bill_first_name = db.Column(db.String(), nullable=False, default="")
    bill_last_name = db.Column(db.String(), nullable=False, default="")
    student_name = db.Column(db.String(), nullable=False, default="")
    product_name = db.Column(db.String(), nullable=False, default="")
    quantity = db.Column(db.Integer(), nullable=False, default=1)
    images = db.Column(db.String(), nullable=False, default="")
    ship_address1 = db.Column(db.String(), nullable=False, default="")
    ship_address2 = db.Column(db.String(), nullable=False, default="")
    ship_city = db.Column(db.String(), nullable=False, default="")
    ship_state = db.Column(db.String(), nullable=False, default="")
    ship_zip = db.Column(db.String(), nullable=False, default="")
    description = db.Column(db.String(), nullable=False, default="")
    active = db.Column(db.Boolean(), nullable=False, default=True)
    imported_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    task = db.relationship("Task", backref="order_lines")

    def __init__(
        self,
        company_id,
        task_id,
        proofpix_order_number="",
        event_name="",
        bill_first_name="",
        bill_last_name="",
        student_name="",
        product_name="",
        quantity=1,
        images="",
        ship_address1="",
        ship_address2="",
        ship_city="",
        ship_state="",
        ship_zip="",
        description="",
        active=True,
    ):
        self.company_id = company_id
        self.task_id = task_id
        self.proofpix_order_number = proofpix_order_number
        self.event_name = event_name
        self.bill_first_name = bill_first_name
        self.bill_last_name = bill_last_name
        self.student_name = student_name
        self.product_name = product_name
        self.quantity = quantity
        self.images = images
        self.ship_address1 = ship_address1
        self.ship_address2 = ship_address2
        self.ship_city = ship_city
        self.ship_state = ship_state
        self.ship_zip = ship_zip
        self.description = description
        self.active = active


class OrderLineSchema(ma.Schema):
    display_label = ma.fields.Method("get_display_label")
    ship_to = ma.fields.Method("get_ship_to")

    class Meta:
        fields = (
            "order_line_id",
            "company_id",
            "task_id",
            "proofpix_order_number",
            "event_name",
            "bill_first_name",
            "bill_last_name",
            "student_name",
            "product_name",
            "quantity",
            "images",
            "ship_address1",
            "ship_address2",
            "ship_city",
            "ship_state",
            "ship_zip",
            "description",
            "display_label",
            "ship_to",
            "imported_at",
            "updated_at",
        )

    def get_display_label(self, obj):
        name = (obj.student_name or "").strip()
        if not name:
            name = " ".join(
                part
                for part in [(obj.bill_first_name or "").strip(), (obj.bill_last_name or "").strip()]
                if part
            ).strip()
        product = (obj.product_name or "").strip() or "Order"
        qty = obj.quantity or 1
        images = (obj.images or "").strip()
        label = f"{name} — {product} × {qty}" if name else f"{product} × {qty}"
        if images:
            label = f"{label} — Img {images}"
        return label

    def get_ship_to(self, obj):
        parts = [
            (obj.ship_address1 or "").strip(),
            (obj.ship_address2 or "").strip(),
            " ".join(
                part
                for part in [
                    (obj.ship_city or "").strip(),
                    (obj.ship_state or "").strip(),
                    (obj.ship_zip or "").strip(),
                ]
                if part
            ).strip(),
        ]
        return ", ".join(part for part in parts if part)


order_line_schema = OrderLineSchema()
order_lines_schema = OrderLineSchema(many=True)
