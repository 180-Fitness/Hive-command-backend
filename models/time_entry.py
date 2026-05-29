import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class TimeEntry(db.Model):
    __tablename__ = "time_entries"

    time_entry_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tasks.task_id"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    hours = db.Column(db.Float(), nullable=False)
    notes = db.Column(db.String(), default="")
    logged_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    task = db.relationship("Task", back_populates="time_entries")
    user = db.relationship("AppUser")

    def __init__(self, company_id, task_id, user_id, hours, notes=""):
        self.company_id = company_id
        self.task_id = task_id
        self.user_id = user_id
        self.hours = hours
        self.notes = notes


class TimeEntrySchema(ma.Schema):
    class Meta:
        fields = ("time_entry_id", "company_id", "task_id", "user_id", "hours", "notes", "logged_at")


time_entry_schema = TimeEntrySchema()
time_entries_schema = TimeEntrySchema(many=True)
