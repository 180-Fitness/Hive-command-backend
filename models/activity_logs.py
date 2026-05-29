import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    activity_log_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    action = db.Column(db.String(), nullable=False)
    detail = db.Column(db.String(), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, user_id, company_id, action, detail=""):
        self.user_id = user_id
        self.company_id = company_id
        self.action = action
        self.detail = detail


class ActivityLogSchema(ma.Schema):
    class Meta:
        fields = ("activity_log_id", "user_id", "company_id", "action", "detail", "created_at")


activity_log_schema = ActivityLogSchema()
