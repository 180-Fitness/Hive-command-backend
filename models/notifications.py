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
    message = db.Column(db.String(), nullable=False)
    read = db.Column(db.Boolean(), nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    receiver = db.relationship("AppUser")

    def __init__(self, receiver_id, message, read=False):
        self.receiver_id = receiver_id
        self.message = message
        self.read = read


class NotificationSchema(ma.Schema):
    class Meta:
        fields = ("notification_id", "receiver_id", "message", "read", "created_at")


notification_schema = NotificationSchema()
notifications_schema = NotificationSchema(many=True)
