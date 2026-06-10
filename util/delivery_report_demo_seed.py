"""Seed a test month of White Raven school shoots for the delivery report demo."""

from datetime import date, datetime, time, timezone

import config
from db import db
from models.app_users import AppUser
from models.calendar_events import FALL_PICTURE_DAY, CalendarEvent
from models.companies import Company
from models.task_statuses import TaskStatus
from models.tasks import Task
from util.school_picture_workflow import sync_school_picture_assignee
from util.white_raven_calendar_sync import sync_calendar_event_to_task

DEMO_SOURCE = "demo_delivery_report"
DEMO_COMPANY_NAME = "White Raven"

# Each entry: school, shoot date (YYYY-MM-DD), pipeline status, optional completion date.
DEMO_SCHOOLS = [
    ("Gunnison Valley High", "2026-05-01", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-15"),
    ("Manti High School", "2026-05-02", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-23"),
    ("Richfield High", "2026-05-05", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-28"),
    ("Delta High", "2026-05-06", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-20"),
    ("Fillmore High", "2026-05-07", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-28"),
    ("Nephi High", "2026-05-08", config.SCHOOL_PICTURE_STAGE_DONE, "2026-06-02"),
    ("Payson High", "2026-05-09", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-25"),
    ("Spanish Fork High", "2026-05-12", config.SCHOOL_PICTURE_STAGE_DONE, "2026-06-02"),
    ("Springville High", "2026-05-13", config.SCHOOL_PICTURE_STAGE_DONE, "2026-06-05"),
    ("Salem Hills High", "2026-05-14", config.SCHOOL_PICTURE_STAGE_DONE, "2026-05-28"),
    ("Maple Mountain High", "2026-05-15", config.SCHOOL_PICTURE_STAGE_DONE, "2026-06-05"),
    ("Timpanogos High", "2026-05-16", config.SCHOOL_PICTURE_STAGE_DONE, "2026-06-08"),
    ("Pleasant Grove High", "2026-05-01", config.SCHOOL_PICTURE_STAGE_QC, None),
    ("American Fork High", "2026-05-08", config.SCHOOL_PICTURE_STAGE_PRINT, None),
    ("Lehi High", "2026-05-15", config.SCHOOL_PICTURE_STAGE_ONLINE, None),
    ("Orem High", "2026-05-19", config.SCHOOL_PICTURE_STAGE_ONLINE, None),
    ("Timpview High", "2026-05-20", config.SCHOOL_PICTURE_STAGE_PRINT, None),
    ("Provo High", "2026-05-21", config.SCHOOL_PICTURE_STAGE_QC, None),
    ("Lone Peak High", "2026-05-22", config.SCHOOL_PICTURE_STAGE_PICTURES, None),
]


def _default_demo_month():
    if DEMO_SCHOOLS:
        return datetime.strptime(DEMO_SCHOOLS[0][1], "%Y-%m-%d").date().replace(day=1)
    return date.today().replace(day=1)


def _resolve_actor(company_id):
    admin = (
        db.session.query(AppUser)
        .filter(AppUser.active.is_(True))
        .filter(AppUser.email == config.admin_email)
        .first()
    )
    if admin:
        return admin

    return (
        db.session.query(AppUser)
        .filter(AppUser.active.is_(True))
        .filter(AppUser.company_id == company_id)
        .first()
    )


def _status_for_company(company_id, status_name):
    return (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .filter(TaskStatus.name == status_name)
        .first()
    )


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _as_utc_timestamp(value):
    return datetime.combine(value, time(hour=12), tzinfo=timezone.utc)


def clear_delivery_report_demo(company_name=DEMO_COMPANY_NAME):
    company = (
        db.session.query(Company)
        .filter(Company.name == company_name)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        return {"removed_events": 0, "removed_tasks": 0}

    events = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.company_id == company.company_id)
        .filter(CalendarEvent.source == DEMO_SOURCE)
        .all()
    )
    event_ids = [event.calendar_event_id for event in events]

    removed_tasks = 0
    if event_ids:
        tasks = (
            db.session.query(Task)
            .filter(Task.calendar_event_id.in_(event_ids))
            .all()
        )
        for task in tasks:
            task.active = False
            removed_tasks += 1

    removed_events = 0
    for event in events:
        event.active = False
        removed_events += 1

    if removed_events or removed_tasks:
        db.session.commit()

    return {"removed_events": removed_events, "removed_tasks": removed_tasks}


def seed_delivery_report_demo(month_start=None, company_name=DEMO_COMPANY_NAME, replace=True):
    month_start = month_start or _default_demo_month()
    if month_start.day != 1:
        month_start = month_start.replace(day=1)

    company = (
        db.session.query(Company)
        .filter(Company.name == company_name)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        raise ValueError(f"Company not found: {company_name}")

    actor = _resolve_actor(company.company_id)
    if not actor:
        raise ValueError("No active user found to own demo calendar events")

    if replace:
        clear_delivery_report_demo(company_name=company_name)

    created_events = 0
    created_tasks = 0
    finished = 0
    in_progress = 0

    for school, shoot_on, status_name, completed_on in DEMO_SCHOOLS:
        shoot_date = _parse_date(shoot_on)
        if shoot_date.replace(day=1) != month_start:
            continue

        status = _status_for_company(company.company_id, status_name)
        if not status:
            raise ValueError(f"Missing task status '{status_name}' for {company_name}")

        event = CalendarEvent(
            company_id=company.company_id,
            title=f"{school} Fall Picture Day",
            school=school,
            event_type=FALL_PICTURE_DAY,
            event_date=shoot_date,
            created_by_id=actor.user_id,
            num_students=450,
            num_stations=4,
            location=f"{school} gymnasium",
            source=DEMO_SOURCE,
        )
        db.session.add(event)
        db.session.flush()
        created_events += 1

        task = sync_calendar_event_to_task(event, actor.user_id)
        if not task:
            raise RuntimeError(f"Failed to sync demo task for {school}")

        task.task_status_id = status.task_status_id
        sync_school_picture_assignee(task, company)
        created_tasks += 1

        if status_name == config.SCHOOL_PICTURE_STAGE_DONE:
            finished += 1
            if completed_on:
                task.updated_at = _as_utc_timestamp(_parse_date(completed_on))
        else:
            in_progress += 1

    db.session.commit()

    return {
        "company_id": str(company.company_id),
        "company_name": company.name,
        "month": month_start.strftime("%Y-%m"),
        "created_events": created_events,
        "created_tasks": created_tasks,
        "finished": finished,
        "in_progress": in_progress,
    }
