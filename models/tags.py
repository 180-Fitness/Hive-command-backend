import uuid

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db
from models.task_tag_xref import task_tags


class Tag(db.Model):
    __tablename__ = "tags"

    tag_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    name = db.Column(db.String(), nullable=False)
    active = db.Column(db.Boolean(), nullable=False, default=True)

    company = db.relationship("Company", back_populates="tags")
    tasks = db.relationship("Task", secondary=task_tags, back_populates="tags")

    def __init__(self, company_id, name, active=True):
        self.company_id = company_id
        self.name = name
        self.active = active


class TagSchema(ma.Schema):
    class Meta:
        fields = ("tag_id", "company_id", "name", "active")


tag_schema = TagSchema()
tags_schema = TagSchema(many=True)
