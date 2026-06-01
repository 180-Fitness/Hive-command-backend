from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from db import db

user_companies = Table(
    "user_companies",
    db.Model.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("app_users.user_id"), primary_key=True),
    Column("company_id", UUID(as_uuid=True), ForeignKey("companies.company_id"), primary_key=True),
)
