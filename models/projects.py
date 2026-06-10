import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Project(db.Model):
    __tablename__ = "projects"

    project_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    client_id = db.Column(UUID(as_uuid=True), db.ForeignKey("clients.client_id"), nullable=True)
    name = db.Column(db.String(), nullable=False)
    color = db.Column(db.String(), nullable=False, default="#2563EB")
    description = db.Column(db.String(), nullable=False, default="")
    active = db.Column(db.Boolean(), nullable=False, default=True)
    user_deleted = db.Column(db.Boolean(), nullable=False, default=False)
    created_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="projects")
    client = db.relationship("Client", back_populates="projects")
    created_by = db.relationship("AppUser", foreign_keys=[created_by_id])
    tasks = db.relationship("Task", back_populates="project", cascade="all, delete-orphan")

    def __init__(
        self,
        company_id,
        name,
        created_by_id,
        color="#2563EB",
        description="",
        client_id=None,
        active=True,
        user_deleted=False,
    ):
        self.company_id = company_id
        self.name = name
        self.created_by_id = created_by_id
        self.color = color
        self.description = description
        self.client_id = client_id
        self.active = active
        self.user_deleted = user_deleted


class ProjectSchema(ma.Schema):
    class Meta:
        fields = (
            "project_id",
            "company_id",
            "client_id",
            "name",
            "color",
            "description",
            "active",
            "created_by_id",
            "created_at",
        )


project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)
