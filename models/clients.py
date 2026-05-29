import uuid

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db


class Client(db.Model):
    __tablename__ = "clients"

    client_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    name = db.Column(db.String(), nullable=False)
    active = db.Column(db.Boolean(), nullable=False, default=True)

    projects = db.relationship("Project", back_populates="client")

    def __init__(self, company_id, name, active=True):
        self.company_id = company_id
        self.name = name
        self.active = active


class ClientSchema(ma.Schema):
    class Meta:
        fields = ("client_id", "company_id", "name", "active")


client_schema = ClientSchema()
clients_schema = ClientSchema(many=True)
