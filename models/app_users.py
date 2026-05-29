import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import joinedload

from db import db
from models.task_assignment_xref import task_assignments
from models.user_companies_xref import user_companies


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

    company = db.relationship("Company", back_populates="users", foreign_keys=[company_id])
    assigned_companies = db.relationship(
        "Company",
        secondary=user_companies,
        lazy="joined",
    )
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
    company_ids = ma.fields.Method("get_company_ids")

    class Meta:
        fields = (
            "user_id",
            "enterprise_id",
            "company_id",
            "company_ids",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "color",
            "active",
            "created_at",
        )

    def get_company_ids(self, obj):
        if obj.assigned_companies:
            return [str(company.company_id) for company in obj.assigned_companies]
        if obj.company_id:
            return [str(obj.company_id)]
        return []


class AppUserAssigneeSchema(ma.Schema):
    class Meta:
        fields = ("user_id", "first_name", "last_name", "email", "color")


user_schema = AppUserSchema()
users_schema = AppUserSchema(many=True)
assignee_schema = AppUserAssigneeSchema()
assignees_schema = AppUserAssigneeSchema(many=True)


def users_with_companies_query():
    return db.session.query(AppUser).options(joinedload(AppUser.assigned_companies))
