import uuid

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class TaskStatus(db.Model):
    __tablename__ = "task_statuses"

    task_status_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    name = db.Column(db.String(), nullable=False)
    color = db.Column(db.String(), nullable=False, default="#64748B")
    is_default = db.Column(db.Boolean(), nullable=False, default=False)
    sort_order = db.Column(db.Integer(), nullable=False, default=0)

    company = db.relationship("Company", back_populates="task_statuses")
    tasks = db.relationship("Task", back_populates="status")

    def __init__(self, company_id, name, color="#64748B", is_default=False, sort_order=0):
        self.company_id = company_id
        self.name = name
        self.color = color
        self.is_default = is_default
        self.sort_order = sort_order


class TaskStatusSchema(ma.Schema):
    class Meta:
        fields = ("task_status_id", "company_id", "name", "color", "is_default", "sort_order")


task_status_schema = TaskStatusSchema()
task_statuses_schema = TaskStatusSchema(many=True)
