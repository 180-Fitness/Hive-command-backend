from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from db import db

task_tags = Table(
    "task_tags",
    db.Model.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey("tasks.task_id"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.tag_id"), primary_key=True),
)
