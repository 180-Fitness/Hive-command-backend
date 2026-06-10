import uuid
from datetime import datetime, timezone

import marshmallow as ma
from sqlalchemy.dialects.postgresql import UUID

from db import db

SPRING_PICTURE_DAY = "Spring Picture Day"
FALL_PICTURE_DAY = "Fall Picture Day"
RETAKE_PICTURE_DAY = "Retake"
GRADUATION = "Graduation"
ROOFTOP = "Rooftop"
SPORTS = "Sports"
SENIOR_PICTURES = "Senior Pictures"

# Legacy label still stored on some synced events
RETAKE_FALL_PICTURE_DAY = "Retake Fall Picture Day"

PICTURE_DAY_TYPES = (
    SPRING_PICTURE_DAY,
    FALL_PICTURE_DAY,
    RETAKE_PICTURE_DAY,
    GRADUATION,
    ROOFTOP,
    SPORTS,
    SENIOR_PICTURES,
)

SHOOT_EVENT_TYPES = PICTURE_DAY_TYPES + (RETAKE_FALL_PICTURE_DAY,)


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"

    calendar_event_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False
    )
    company_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("companies.company_id"), nullable=False
    )
    title = db.Column(db.String(), nullable=False)
    school = db.Column(db.String(), nullable=False, default="")
    event_type = db.Column(db.String(), nullable=False, default="")
    description = db.Column(db.String(), nullable=False, default="")
    event_date = db.Column(db.Date, nullable=False)
    num_stations = db.Column(db.Integer(), nullable=True)
    num_students = db.Column(db.Integer(), nullable=True)
    location = db.Column(db.String(), nullable=False, default="")
    # sh/shoot-day-sms-reminders
    # contact_phone = db.Column(db.String(), nullable=False, default="")
    # shoot_reminder_sms_sent_at = db.Column(db.DateTime, nullable=True)
    project_id = db.Column(
        UUID(as_uuid=True), db.ForeignKey("projects.project_id"), nullable=True
    )
    source = db.Column(db.String(), nullable=False, default="manual")
    active = db.Column(db.Boolean(), nullable=False, default=True)
    created_by_id = db.Column(UUID(as_uuid=True), db.ForeignKey("app_users.user_id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    created_by = db.relationship("AppUser", foreign_keys=[created_by_id])
    project = db.relationship("Project", foreign_keys=[project_id])

    def __init__(
        self,
        company_id,
        title,
        event_date,
        created_by_id,
        school="",
        event_type="",
        description="",
        num_stations=None,
        num_students=None,
        location="",
        project_id=None,
        source="manual",
        active=True,
    ):
        self.company_id = company_id
        self.title = title
        self.event_date = event_date
        self.created_by_id = created_by_id
        self.school = school
        self.event_type = event_type
        self.description = description
        self.num_stations = num_stations
        self.num_students = num_students
        self.location = location
        self.project_id = project_id
        self.source = source
        self.active = active


class CalendarEventSchema(ma.Schema):
    formatted_date = ma.fields.Method("get_formatted_date")

    class Meta:
        fields = (
            "calendar_event_id",
            "company_id",
            "title",
            "school",
            "event_type",
            "description",
            "event_date",
            "formatted_date",
            "num_stations",
            "num_students",
            "location",
            "project_id",
            "source",
            "active",
            "created_by_id",
            "created_at",
            "updated_at",
        )

    def get_formatted_date(self, obj):
        if not obj.event_date:
            return ""
        return obj.event_date.strftime("%B %d, %Y")


calendar_event_schema = CalendarEventSchema()
calendar_events_schema = CalendarEventSchema(many=True)
