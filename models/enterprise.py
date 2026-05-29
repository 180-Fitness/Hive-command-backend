import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Enterprise(db.Model):
    """Single parent tenant for this deployment."""

    __tablename__ = "enterprise"

    enterprise_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    name = db.Column(db.String(), nullable=False, unique=True)
    email = db.Column(db.String(), nullable=False)
    phone = db.Column(db.String(), nullable=False, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    companies = db.relationship("Company", back_populates="enterprise")

    def __init__(self, name, email, phone=""):
        self.name = name
        self.email = email
        self.phone = phone


class EnterpriseSchema(ma.Schema):
    class Meta:
        fields = ("enterprise_id", "name", "email", "phone", "created_at")


enterprise_schema = EnterpriseSchema()
