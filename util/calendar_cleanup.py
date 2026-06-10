"""Deactivate legacy calendar imports and their linked school tasks."""

from db import db
from models.calendar_events import CalendarEvent
from models.companies import Company
from models.projects import Project
from models.tasks import Task

DEFAULT_KEEP_SOURCES = ("demo_delivery_report",)


def clear_legacy_calendar_data(
    company_name="White Raven",
    keep_sources=DEFAULT_KEEP_SOURCES,
):
    company = (
        db.session.query(Company)
        .filter(Company.name == company_name)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        raise ValueError(f"Company not found: {company_name}")

    keep_sources = tuple(keep_sources or ())

    legacy_events = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.company_id == company.company_id)
        .filter(CalendarEvent.active.is_(True))
        .filter(~CalendarEvent.source.in_(keep_sources))
        .all()
    )
    legacy_event_ids = [event.calendar_event_id for event in legacy_events]

    removed_tasks = 0
    if legacy_event_ids:
        tasks = (
            db.session.query(Task)
            .filter(Task.company_id == company.company_id)
            .filter(Task.calendar_event_id.in_(legacy_event_ids))
            .filter(Task.active.is_(True))
            .all()
        )
        for task in tasks:
            task.active = False
            removed_tasks += 1

    removed_events = 0
    for event in legacy_events:
        event.active = False
        removed_events += 1

    removed_projects = 0
    projects = (
        db.session.query(Project)
        .filter(Project.company_id == company.company_id)
        .filter(Project.active.is_(True))
        .all()
    )
    for project in projects:
        has_active_tasks = (
            db.session.query(Task.task_id)
            .filter(Task.project_id == project.project_id)
            .filter(Task.active.is_(True))
            .first()
            is not None
        )
        if not has_active_tasks:
            project.active = False
            removed_projects += 1

    if removed_events or removed_tasks or removed_projects:
        db.session.commit()

    remaining_events = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.company_id == company.company_id)
        .filter(CalendarEvent.active.is_(True))
        .count()
    )
    remaining_tasks = (
        db.session.query(Task)
        .filter(Task.company_id == company.company_id)
        .filter(Task.active.is_(True))
        .filter(Task.calendar_event_id.isnot(None))
        .count()
    )

    return {
        "company_id": str(company.company_id),
        "company_name": company.name,
        "removed_events": removed_events,
        "removed_tasks": removed_tasks,
        "removed_projects": removed_projects,
        "remaining_events": remaining_events,
        "remaining_tasks": remaining_tasks,
    }
