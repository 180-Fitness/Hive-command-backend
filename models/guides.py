import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Guide(db.Model):
    __tablename__ = "guides"

    guide_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    title = db.Column(db.String(), nullable=False)
    summary = db.Column(db.String(), nullable=False, default="")
    body = db.Column(db.String(), nullable=False, default="")
    sort_order = db.Column(db.Integer(), nullable=False, default=0)
    active = db.Column(db.Boolean(), nullable=False, default=True)
    created_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    created_by = db.relationship("AppUser", foreign_keys=[created_by_id])

    def __init__(
        self,
        company_id,
        title,
        created_by_id,
        summary="",
        body="",
        sort_order=0,
        active=True,
    ):
        self.company_id = company_id
        self.title = title
        self.created_by_id = created_by_id
        self.summary = summary
        self.body = body
        self.sort_order = sort_order
        self.active = active


class GuideSchema(ma.Schema):
    class Meta:
        fields = (
            "guide_id",
            "company_id",
            "title",
            "summary",
            "body",
            "sort_order",
            "active",
            "created_by_id",
            "created_at",
            "updated_at",
        )


class GuideListSchema(ma.Schema):
    class Meta:
        fields = (
            "guide_id",
            "company_id",
            "title",
            "summary",
            "sort_order",
            "active",
            "created_at",
            "updated_at",
        )


guide_schema = GuideSchema()
guides_schema = GuideListSchema(many=True)
