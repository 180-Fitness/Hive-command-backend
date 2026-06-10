import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Notification(db.Model):
    __tablename__ = "notifications"

    notification_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    receiver_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    company_id = db.Column(UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=True)
    calendar_event_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("calendar_events.calendar_event_id"), nullable=True
    )
    notification_type = db.Column(db.String(), nullable=False, default="general")
    message = db.Column(db.String(), nullable=False)
    link = db.Column(db.String(), nullable=False, default="/calendar")
    read = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    receiver = db.relationship("AppUser")

    def __init__(
        self,
        receiver_id,
        message,
        read=False,
        company_id=None,
        calendar_event_id=None,
        notification_type="general",
        link="/calendar",
    ):
        self.receiver_id = receiver_id
        self.message = message
        self.read = read
        self.company_id = company_id
        self.calendar_event_id = calendar_event_id
        self.notification_type = notification_type
        self.link = link


class NotificationSchema(ma.Schema):
    class Meta:
        fields = (
            "notification_id",
            "receiver_id",
            "company_id",
            "calendar_event_id",
            "notification_type",
            "message",
            "link",
            "read",
            "created_at",
        )


notification_schema = NotificationSchema()
notifications_schema = NotificationSchema(many=True)
