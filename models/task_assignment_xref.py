from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from db import db

task_assignments = Table(
    "task_assignments",
    db.Model.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey("tasks.task_id"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("app_users.user_id"), primary_key=True),
)
