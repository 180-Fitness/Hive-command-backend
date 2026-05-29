from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from db import db

task_sprints = Table(
    "task_sprints",
    db.Model.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey("tasks.task_id"), primary_key=True),
    Column("sprint_id", UUID(as_uuid=True), ForeignKey("sprints.sprint_id"), primary_key=True),
)
