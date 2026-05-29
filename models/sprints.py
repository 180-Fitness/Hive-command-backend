import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db
from models.tasks_sprints_xref import task_sprints


class Sprint(db.Model):
    __tablename__ = "sprints"

    sprint_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    name = db.Column(db.String(), nullable=False)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean(), nullable=False, default=True)
    created_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="sprints")
    tasks = db.relationship("Task", secondary=task_sprints, back_populates="sprints")

    def __init__(self, company_id, name, created_by_id, start_date=None, end_date=None, active=True):
        self.company_id = company_id
        self.name = name
        self.created_by_id = created_by_id
        self.start_date = start_date
        self.end_date = end_date
        self.active = active


class SprintSchema(ma.Schema):
    class Meta:
        fields = (
            "sprint_id",
            "company_id",
            "name",
            "start_date",
            "end_date",
            "active",
            "created_by_id",
            "created_at",
        )


sprint_schema = SprintSchema()
sprints_schema = SprintSchema(many=True)
