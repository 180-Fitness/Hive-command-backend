import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db
from models.task_assignment_xref import task_assignments


class AppUser(db.Model):
    __tablename__ = "app_users"

    user_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    enterprise_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("enterprise.enterprise_id"), nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    first_name = db.Column(db.String(), nullable=False)
    last_name = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), nullable=False, unique=True)
    phone = db.Column(db.String(), default="")
    password = db.Column(db.String(), nullable=False)
    role = db.Column(db.String(), nullable=False, default="member")
    color = db.Column(db.String(), nullable=False, default="#2563EB")
    active = db.Column(db.Boolean(), nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="users")
    sessions = db.relationship("AuthTokens", back_populates="user", cascade="all, delete-orphan")
    created_tasks = db.relationship("Task", back_populates="created_by")
    assigned_tasks = db.relationship(
        "Task", secondary=task_assignments, back_populates="assignees"
    )

    def __init__(
        self,
        enterprise_id,
        company_id,
        first_name,
        last_name,
        email,
        password,
        phone="",
        role="member",
        color="#2563EB",
        active=True,
    ):
        self.enterprise_id = enterprise_id
        self.company_id = company_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.phone = phone
        self.role = role
        self.color = color
        self.active = active


class AppUserSchema(ma.Schema):
    class Meta:
        fields = (
            "user_id",
            "enterprise_id",
            "company_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "color",
            "active",
            "created_at",
        )


class AppUserAssigneeSchema(ma.Schema):
    class Meta:
        fields = ("user_id", "first_name", "last_name", "email", "color")


user_schema = AppUserSchema()
users_schema = AppUserSchema(many=True)
assignee_schema = AppUserAssigneeSchema()
assignees_schema = AppUserAssigneeSchema(many=True)
