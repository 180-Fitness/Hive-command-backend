import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Comment(db.Model):
    __tablename__ = "comments"

    comment_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    task_id = db.Column(UUID(as_uuid=True), db.ForeignKey("tasks.task_id"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    body = db.Column(db.String(), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    task = db.relationship("Task", back_populates="comments")
    author = db.relationship("AppUser")

    def __init__(self, task_id, user_id, body):
        self.task_id = task_id
        self.user_id = user_id
        self.body = body


class CommentSchema(ma.Schema):
    class Meta:
        fields = ("comment_id", "task_id", "user_id", "body", "created_at")


class CommentDetailSchema(CommentSchema):
    class Meta:
        fields = ("comment_id", "task_id", "user_id", "body", "created_at", "author")

    author = ma.fields.Nested(
        "AppUserSchema", only=["user_id", "first_name", "last_name", "color"]
    )


comment_schema = CommentSchema()
comment_detail_schema = CommentDetailSchema()
comments_schema = CommentSchema(many=True)
comments_detail_schema = CommentDetailSchema(many=True)
