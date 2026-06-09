from datetime import date, timedelta

from db import db
from models.app_users import AppUser
from models.calendar_events import CalendarEvent
from models.notifications import Notification
from util.access_control import COMPANY_ADMIN, ENTERPRISE_ADMIN
from util.user_companies import get_user_company_ids

CALENDAR_REMINDER_TYPE = "calendar_reminder"


def _sunday_before(event_date):
    """Return the Sunday immediately before picture day (7 days prior if event is on Sunday)."""
    days_back = (event_date.weekday() + 1) % 7 or 7
    return event_date - timedelta(days=days_back)


def _days_until_label(days):
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"


def _format_reminder_message(event, days_until):
    formatted = event.event_date.strftime("%B %d, %Y")
    when = _days_until_label(days_until)
    school = event.school or event.title
    event_type = event.event_type or "Picture day"
    parts = [
        f"Remind the photographer: {school} — {event_type} is {when} ({formatted})."
    ]
    if event.location:
        parts.append(f"Location: {event.location}.")
    if event.num_students is not None:
        parts.append(f"Students: {event.num_students}.")
    if event.num_stations is not None:
        parts.append(f"Stations: {event.num_stations}.")
    return " ".join(parts)


def company_admin_user_ids(company_id):
    from models.companies import Company

    company = db.session.query(Company).filter(Company.company_id == company_id).first()
    if not company:
        return []

    admins = (
        db.session.query(AppUser)
        .filter(AppUser.active.is_(True))
        .filter(AppUser.role.in_([COMPANY_ADMIN, ENTERPRISE_ADMIN]))
        .filter(AppUser.enterprise_id == company.enterprise_id)
        .all()
    )

    ids = []
    for user in admins:
        if user.role == ENTERPRISE_ADMIN:
            ids.append(user.user_id)
            continue
        if str(company_id) in get_user_company_ids(user):
            ids.append(user.user_id)
    return ids


def generate_calendar_reminders(company_id=None):
    """Create reminder notifications on the Sunday before each upcoming picture day."""
    if not company_id:
        return 0

    today = date.today()
    if today.weekday() != 6:
        return 0

    week_end = today + timedelta(days=7)

    events = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.active.is_(True))
        .filter(CalendarEvent.company_id == company_id)
        .filter(CalendarEvent.event_date > today)
        .filter(CalendarEvent.event_date <= week_end)
        .order_by(CalendarEvent.event_date.asc())
        .all()
    )
    events = [event for event in events if _sunday_before(event.event_date) == today]

    if not events:
        return 0

    admin_ids = company_admin_user_ids(company_id)
    if not admin_ids:
        return 0

    created = 0
    for event in events:
        days_until = (event.event_date - today).days
        message = _format_reminder_message(event, days_until)
        for admin_id in admin_ids:
            exists = (
                db.session.query(Notification)
                .filter(Notification.receiver_id == admin_id)
                .filter(Notification.calendar_event_id == event.calendar_event_id)
                .filter(Notification.notification_type == CALENDAR_REMINDER_TYPE)
                .first()
            )
            if exists:
                continue

            db.session.add(
                Notification(
                    receiver_id=admin_id,
                    company_id=company_id,
                    calendar_event_id=event.calendar_event_id,
                    notification_type=CALENDAR_REMINDER_TYPE,
                    message=message,
                    link="/calendar",
                )
            )
            created += 1

    if created:
        db.session.commit()
    return created
