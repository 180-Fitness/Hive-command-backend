import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Company(db.Model):
    """Subsidiary or division within the enterprise."""

    __tablename__ = "companies"

    company_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    enterprise_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("enterprise.enterprise_id"), nullable=False
    )
    name = db.Column(db.String(), nullable=False)
    code = db.Column(db.String(), nullable=True)
    phone = db.Column(db.String(), nullable=False, default="")
    email = db.Column(db.String(), nullable=False, default="")
    city = db.Column(db.String(), nullable=False, default="")
    state = db.Column(db.String(), nullable=False, default="")
    postal = db.Column(db.String(), nullable=False, default="")
    color = db.Column(db.String(), nullable=False, default="#2563EB")
    active = db.Column(db.Boolean(), nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    enterprise = db.relationship("Enterprise", back_populates="companies")
    users = db.relationship("AppUser", back_populates="company")
    projects = db.relationship("Project", back_populates="company")
    task_statuses = db.relationship("TaskStatus", back_populates="company")
    tags = db.relationship("Tag", back_populates="company")
    sprints = db.relationship("Sprint", back_populates="company")

    def __init__(
        self,
        enterprise_id,
        name,
        phone="",
        email="",
        city="",
        state="",
        postal="",
        color="#2563EB",
        code=None,
        active=True,
    ):
        self.enterprise_id = enterprise_id
        self.name = name
        self.phone = phone
        self.email = email
        self.city = city
        self.state = state
        self.postal = postal
        self.color = color
        self.code = code
        self.active = active

    @staticmethod
    def blank(enterprise_id):
        return Company(enterprise_id, "")


class CompanySchema(ma.Schema):
    class Meta:
        fields = (
            "company_id",
            "enterprise_id",
            "name",
            "code",
            "phone",
            "email",
            "city",
            "state",
            "postal",
            "color",
            "active",
            "created_at",
        )


company_schema = CompanySchema()
companies_schema = CompanySchema(many=True)
