import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db
from models.task_assignment_xref import task_assignments
from models.task_tag_xref import task_tags
from models.tasks_sprints_xref import task_sprints


class Task(db.Model):
    __tablename__ = "tasks"

    task_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    project_id = db.Column(UUID(as_uuid=True), db.ForeignKey("projects.project_id"), nullable=True)
    task_status_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("task_statuses.task_status_id"), nullable=False
    )
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String(), nullable=False, default="")
    points_estimate = db.Column(db.Float(), nullable=True)
    due_date = db.Column(db.Date(), nullable=True)
    delivery_date = db.Column(db.Date(), nullable=True)
    delivery_picked_up_by = db.Column(db.String(), nullable=False, default="")
    calendar_event_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("calendar_events.calendar_event_id"), nullable=True
    )
    created_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    active = db.Column(db.Boolean(), nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project = db.relationship("Project", back_populates="tasks")
    status = db.relationship("TaskStatus", back_populates="tasks")
    created_by = db.relationship("AppUser", back_populates="created_tasks", foreign_keys=[created_by_id])
    assignees = db.relationship(
        "AppUser", secondary=task_assignments, back_populates="assigned_tasks"
    )
    tags = db.relationship("Tag", secondary=task_tags, back_populates="tasks")
    sprints = db.relationship("Sprint", secondary=task_sprints, back_populates="tasks")
    comments = db.relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    time_entries = db.relationship("TimeEntry", back_populates="task", cascade="all, delete-orphan")

    def __init__(
        self,
        company_id,
        name,
        task_status_id,
        created_by_id,
        description="",
        project_id=None,
        points_estimate=None,
        due_date=None,
        delivery_date=None,
        delivery_picked_up_by="",
        calendar_event_id=None,
        active=True,
    ):
        self.company_id = company_id
        self.name = name
        self.task_status_id = task_status_id
        self.created_by_id = created_by_id
        self.description = description
        self.project_id = project_id
        self.points_estimate = points_estimate
        self.due_date = due_date
        self.delivery_date = delivery_date
        self.delivery_picked_up_by = delivery_picked_up_by
        self.calendar_event_id = calendar_event_id
        self.active = active


_LIST_FIELDS = (
    "task_id",
    "company_id",
    "project_id",
    "task_status_id",
    "name",
    "description",
    "points_estimate",
    "due_date",
    "delivery_date",
    "delivery_picked_up_by",
    "calendar_event_id",
    "created_by_id",
    "active",
    "created_at",
    "updated_at",
)


class TaskSchema(ma.Schema):
    class Meta:
        fields = _LIST_FIELDS


class TaskDetailSchema(TaskSchema):
    class Meta:
        fields = (
            *_LIST_FIELDS,
            "status",
            "project",
            "created_by",
            "assignees",
            "comments",
            "sprints",
        )

    status = ma.fields.Nested(
        "TaskStatusSchema", only=["task_status_id", "name", "color"]
    )
    project = ma.fields.Nested("ProjectSchema", only=["project_id", "name", "color"])
    created_by = ma.fields.Nested(
        "AppUserSchema", only=["user_id", "first_name", "last_name", "color"]
    )
    assignees = ma.fields.Nested(
        "AppUserSchema",
        many=True,
        only=["user_id", "first_name", "last_name", "color"],
    )
    comments = ma.fields.Nested("CommentDetailSchema", many=True)
    sprints = ma.fields.Nested(
        "SprintSchema", many=True, only=["sprint_id", "name", "start_date", "end_date"]
    )


task_schema = TaskSchema()
task_detail_schema = TaskDetailSchema()
tasks_schema = TaskSchema(many=True)
