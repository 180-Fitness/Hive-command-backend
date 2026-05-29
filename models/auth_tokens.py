import uuid
from datetime import datetime

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class AuthTokens(db.Model):
    __tablename__ = "auth_tokens"

    auth_token = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    expiration = db.Column(db.DateTime(timezone=True), nullable=False)

    user = db.relationship("AppUser", back_populates="sessions")

    def __init__(self, user_id, expiration):
        self.user_id = user_id
        self.expiration = expiration


class AuthTokensSchema(ma.Schema):
    class Meta:
        fields = ("auth_token", "expiration", "user")

    user = ma.fields.Nested(
        "AppUserSchema",
        only=("user_id", "first_name", "last_name", "role", "company_id"),
    )


auth_token_schema = AuthTokensSchema()
