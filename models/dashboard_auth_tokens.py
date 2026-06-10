import uuid
from datetime import datetime

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class DashboardAuthTokens(db.Model):
    __tablename__ = "dashboard_auth_tokens"

    auth_token = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    username = db.Column(db.String(), nullable=False)
    expiration = db.Column(db.DateTime(timezone=True), nullable=False)

    company = db.relationship("Company")

    def __init__(self, company_id, username, expiration):
        self.company_id = company_id
        self.username = username
        self.expiration = expiration


class DashboardAuthTokensSchema(ma.Schema):
    class Meta:
        fields = ("auth_token", "expiration", "username", "company_id")

    company_id = ma.fields.String()


dashboard_auth_token_schema = DashboardAuthTokensSchema()
