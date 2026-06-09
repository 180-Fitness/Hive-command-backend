from datetime import date, datetime, timedelta, timezone

from flask import Request, Response, jsonify
from sqlalchemy.orm import joinedload

import config
from db import db
from lib.dashboard_authenticate import dashboard_authenticate_return_auth
from models.calendar_events import CalendarEvent
from models.companies import Company, company_schema
from models.dashboard_auth_tokens import DashboardAuthTokens, dashboard_auth_token_schema
from models.tasks import Task
from util.dashboard_accounts import verify_dashboard_credentials
from util.task_workload import is_done_status_name, serialize_workload_task, week_bounds

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _serialize_dashboard_task(task):
    data = serialize_workload_task(task)
    if task.project:
        data["project_name"] = task.project.name
    if task.assignees:
        data["assignees"] = [
            {
                "user_id": str(assignee.user_id),
                "first_name": assignee.first_name,
                "last_name": assignee.last_name,
                "color": assignee.color,
            }
            for assignee in task.assignees
        ]
    return data


def _serialize_calendar_event(event):
    return {
        "calendar_event_id": str(event.calendar_event_id),
        "title": event.title,
        "school": event.school,
        "event_type": event.event_type,
        "event_date": event.event_date.isoformat(),
        "location": event.location,
    }


def _sort_tasks(rows):
    rows.sort(
        key=lambda row: (row.get("due_date") or "9999-99-99", row["name"].lower())
    )


def _purge_expired_dashboard_tokens():
    if not config.purge_expired_auth_tokens:
        return

    now = datetime.now(timezone.utc)
    expired = (
        db.session.query(DashboardAuthTokens)
        .filter(DashboardAuthTokens.expiration < now)
        .all()
    )
    for token in expired:
        db.session.delete(token)


def _build_company_summary(company, today, week_start, week_end):
    tasks = (
        db.session.query(Task)
        .options(
            joinedload(Task.status),
            joinedload(Task.project),
            joinedload(Task.assignees),
            joinedload(Task.sprints),
        )
        .filter(Task.active.is_(True))
        .filter(Task.company_id == company.company_id)
        .all()
    )

    events = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.active.is_(True))
        .filter(CalendarEvent.company_id == company.company_id)
        .filter(CalendarEvent.event_date >= week_start)
        .filter(CalendarEvent.event_date <= week_end)
        .order_by(CalendarEvent.event_date.asc(), CalendarEvent.school.asc())
        .all()
    )

    overdue = []
    due_today = []
    due_rest_of_week = []
    in_progress = []

    for task in tasks:
        if task.status and is_done_status_name(task.status.name):
            continue

        serialized = _serialize_dashboard_task(task)
        due = task.due_date

        if not due:
            in_progress.append(serialized)
            continue

        if due < today:
            overdue.append(serialized)
        elif due == today:
            due_today.append(serialized)
        elif due <= week_end:
            due_rest_of_week.append(serialized)

    for bucket in (overdue, due_today, due_rest_of_week, in_progress):
        _sort_tasks(bucket)

    return {
        "company_id": str(company.company_id),
        "name": company.name,
        "code": company.code,
        "color": company.color,
        "overdue": overdue,
        "due_today": due_today,
        "due_rest_of_week": due_rest_of_week,
        "in_progress": in_progress,
        "events": [_serialize_calendar_event(event) for event in events],
        "open_count": len(overdue)
        + len(due_today)
        + len(due_rest_of_week)
        + len(in_progress),
    }


def _week_days(today, week_start):
    days = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        days.append(
            {
                "date": day.isoformat(),
                "label": DAY_LABELS[offset],
                "day_of_month": day.day,
                "is_today": day == today,
            }
        )
    return days


def dashboard_auth_add(req: Request) -> Response:
    if req.content_type != "application/json":
        return jsonify({"message": "Request must be JSON"}), 400

    payload = req.get_json() or {}
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        return jsonify({"message": "Invalid dashboard login"}), 401

    verified = verify_dashboard_credentials(username, password)
    if not verified:
        return jsonify({"message": "Invalid username or password"}), 401

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=24)

    _purge_expired_dashboard_tokens()

    session = DashboardAuthTokens(
        company_id=verified["company"].company_id,
        username=verified["username"],
        expiration=expires,
    )
    db.session.add(session)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Dashboard auth success",
                "results": {
                    "auth_info": dashboard_auth_token_schema.dump(session),
                    "company_info": company_schema.dump(verified["company"]),
                },
            }
        ),
        200,
    )


@dashboard_authenticate_return_auth
def dashboard_auth_check_login(req: Request, auth_info) -> Response:
    company = (
        db.session.query(Company)
        .filter(Company.company_id == auth_info.company_id)
        .first()
    )
    if not company:
        return jsonify({"message": "Company not found"}), 404

    return (
        jsonify(
            {
                "message": "Dashboard session valid",
                "results": {
                    "auth_info": dashboard_auth_token_schema.dump(auth_info),
                    "company_info": company_schema.dump(company),
                },
            }
        ),
        200,
    )


@dashboard_authenticate_return_auth
def dashboard_auth_logout(req: Request, auth_info) -> Response:
    db.session.delete(auth_info)
    db.session.commit()
    return jsonify({"message": "Dashboard logged out"}), 200


@dashboard_authenticate_return_auth
def dashboard_week_summary_get(req: Request, auth_info) -> Response:
    company = (
        db.session.query(Company)
        .filter(Company.company_id == auth_info.company_id)
        .filter(Company.active.is_(True))
        .first()
    )
    if not company:
        return jsonify({"message": "Company not found"}), 404

    today = date.today()
    week_start, week_end = week_bounds(today)
    company_summary = _build_company_summary(company, today, week_start, week_end)

    return (
        jsonify(
            {
                "message": "dashboard summary",
                "results": {
                    "today": today.isoformat(),
                    "week_start": week_start.isoformat(),
                    "week_end": week_end.isoformat(),
                    "days": _week_days(today, week_start),
                    "company": company_summary,
                },
            }
        ),
        200,
    )
