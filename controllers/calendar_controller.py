from datetime import date, datetime

from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.calendar_events import (
    CalendarEvent,
    calendar_event_schema,
    calendar_events_schema,
)
from models.projects import Project
from util.access_control import (
    can_access_company_scoped,
    company_scope_filter,
    effective_company_id,
    get_actor,
    is_admin,
    resolve_scope_company_id,
)
from util.calendar_reminders import generate_calendar_reminders
# from util.phone import normalize_phone
# from util.shoot_day_reminders import generate_shoot_day_reminders  # sh/shoot-day-sms-reminders
from util.company_workflow import company_by_id
from util.white_raven_calendar_sync import (
    find_or_create_school_pictures_project,
    promote_due_calendar_shoots_to_sprint,
    school_pictures_project_name,
    sync_calendar_event_to_task,
    sync_company_calendar_shoots,
)
from util.numbers_sync import parse_event_date_from_payload, parse_numbers_calendar
from util.reflection import populate_object
from util.validate_uuid4 import validate_uuid4


def _parse_event_date(payload):
    return parse_event_date_from_payload(payload)


def _parse_optional_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_title(school, event_type, fallback=""):
    school = (school or "").strip()
    event_type = (event_type or "").strip()
    if school and event_type:
        return f"{school} — {event_type}"
    return school or event_type or fallback


def _description_from_location(description, location):
    description = (description or "").strip()
    location = (location or "").strip()
    return description or location


def _parse_project_id(payload, company_id, *, required=True):
    raw = payload.get("project_id")
    if not raw:
        if required:
            return None, (jsonify({"message": "Project is required"}), 400)
        return None, None
    if not validate_uuid4(raw):
        return None, (jsonify({"message": "Invalid project id"}), 400)

    project = (
        db.session.query(Project)
        .filter(Project.project_id == raw)
        .filter(Project.company_id == company_id)
        .filter(Project.active.is_(True))
        .first()
    )
    if not project:
        return None, (jsonify({"message": "Project not found"}), 404)
    return project.project_id, None


def _event_from_payload(payload, *, company_id, created_by_id, source="manual"):
    school = (payload.get("school") or "").strip()
    event_type = (payload.get("event_type") or "").strip()
    title = (payload.get("title") or "").strip() or _build_title(school, event_type)

    if not school:
        return None, (jsonify({"message": "School is required"}), 400)
    if not event_type and source == "manual":
        return None, (jsonify({"message": "Event type is required"}), 400)

    company = company_by_id(company_id)
    if school_pictures_project_name(company):
        project = find_or_create_school_pictures_project(company, created_by_id)
        if not project:
            return None, (
                jsonify({"message": "Could not resolve School Pictures project"}),
                500,
            )
        project_id = project.project_id
    else:
        project_id, project_error = _parse_project_id(
            payload, company_id, required=source == "manual"
        )
        if project_error:
            return None, project_error

    event_date = _parse_event_date(payload)
    if not event_date:
        return None, (
            jsonify({"message": "A valid date (month, day, year) is required"}),
            400,
        )

    location = (payload.get("location") or "").strip()
    # contact_phone = normalize_phone(payload.get("contact_phone", ""))  # sh/shoot-day-sms-reminders
    event = CalendarEvent(
        company_id=company_id,
        title=title or school,
        school=school,
        event_type=event_type,
        event_date=event_date,
        created_by_id=created_by_id,
        description=_description_from_location(payload.get("description"), location),
        num_stations=_parse_optional_int(payload.get("num_stations")),
        num_students=_parse_optional_int(payload.get("num_students")),
        location=location,
        project_id=project_id,
        source=source,
    )
    return event, None


@authenticate_return_auth
def calendar_events_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    query = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.active.is_(True))
        .order_by(CalendarEvent.event_date.asc(), CalendarEvent.school.asc())
    )
    query = company_scope_filter(query, CalendarEvent, actor, scope)

    start = req.args.get("start")
    end = req.args.get("end")
    if start:
        try:
            start_date = datetime.strptime(start[:10], "%Y-%m-%d").date()
            query = query.filter(CalendarEvent.event_date >= start_date)
        except ValueError:
            return jsonify({"message": "Invalid start date"}), 400
    if end:
        try:
            end_date = datetime.strptime(end[:10], "%Y-%m-%d").date()
            query = query.filter(CalendarEvent.event_date <= end_date)
        except ValueError:
            return jsonify({"message": "Invalid end date"}), 400

    if scope:
        sync_company_calendar_shoots(scope, actor.user_id)
        promote_due_calendar_shoots_to_sprint(scope, actor.user_id)

    return jsonify(
        {"message": "events found", "results": calendar_events_schema.dump(query.all())}
    ), 200


@authenticate_return_auth
def calendar_event_get_by_id(req: Request, event_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(event_id):
        return jsonify({"message": "invalid event id"}), 404

    event = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.calendar_event_id == event_id)
        .first()
    )
    if not event or not event.active:
        return jsonify({"message": "event not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, event.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    return jsonify(
        {"message": "event found", "results": calendar_event_schema.dump(event)}
    ), 200


@authenticate_return_auth
def calendar_event_add(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    company_id = effective_company_id(req, actor, payload)
    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    event, error = _event_from_payload(
        payload, company_id=company_id, created_by_id=actor.user_id
    )
    if error:
        return error

    db.session.add(event)
    db.session.flush()
    sync_calendar_event_to_task(event, actor.user_id)
    db.session.commit()
    generate_calendar_reminders(company_id)
    # generate_shoot_day_reminders(company_id)  # sh/shoot-day-sms-reminders
    return jsonify(
        {"message": "event added", "results": calendar_event_schema.dump(event)}
    ), 201


@authenticate_return_auth
def calendar_event_update(req: Request, event_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(event_id):
        return jsonify({"message": "invalid event id"}), 404

    event = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.calendar_event_id == event_id)
        .first()
    )
    if not event or not event.active:
        return jsonify({"message": "event not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, event.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    payload = dict(req.get_json() or {})

    if any(key in payload for key in ("event_date", "month", "day", "year")):
        event_date = _parse_event_date(payload)
        if not event_date:
            return jsonify({"message": "A valid date (month, day, year) is required"}), 400
        # if event.event_date != event_date:
        #     event.shoot_reminder_sms_sent_at = None  # sh/shoot-day-sms-reminders
        event.event_date = event_date
        payload.pop("event_date", None)
        payload.pop("month", None)
        payload.pop("day", None)
        payload.pop("year", None)

    if "num_stations" in payload:
        event.num_stations = _parse_optional_int(payload.pop("num_stations"))
    if "num_students" in payload:
        event.num_students = _parse_optional_int(payload.pop("num_students"))

    company = company_by_id(event.company_id)
    if not school_pictures_project_name(company) and "project_id" in payload:
        project_id, project_error = _parse_project_id(payload, event.company_id)
        if project_error:
            return project_error
        event.project_id = project_id
        payload.pop("project_id")
    else:
        payload.pop("project_id", None)

    payload.pop("source", None)
    error = populate_object(event, payload)
    if error:
        return error

    if "school" in payload:
        event.school = (event.school or "").strip()
    if "event_type" in payload:
        event.event_type = (event.event_type or "").strip()
    if "location" in payload:
        event.location = (event.location or "").strip()
    # if "contact_phone" in payload:  # sh/shoot-day-sms-reminders
    #     previous_phone = event.contact_phone
    #     event.contact_phone = normalize_phone(payload.get("contact_phone", ""))
    #     if event.contact_phone != previous_phone:
    #         event.shoot_reminder_sms_sent_at = None
    if "description" in payload or "location" in payload:
        event.description = _description_from_location(event.description, event.location)

    event.title = _build_title(event.school, event.event_type, event.title)

    sync_calendar_event_to_task(event, actor.user_id)
    db.session.commit()
    # generate_shoot_day_reminders(event.company_id)  # sh/shoot-day-sms-reminders
    return jsonify(
        {"message": "event updated", "results": calendar_event_schema.dump(event)}
    ), 200


@authenticate_return_auth
def calendar_event_delete(req: Request, event_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    if not validate_uuid4(event_id):
        return jsonify({"message": "invalid event id"}), 404

    event = (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.calendar_event_id == event_id)
        .first()
    )
    if not event or not event.active:
        return jsonify({"message": "event not found"}), 404

    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, event.company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    event.active = False
    db.session.commit()
    return jsonify({"message": "event removed"}), 200


@authenticate_return_auth
def calendar_sync_numbers(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor or not is_admin(actor):
        return jsonify({"message": "Forbidden"}), 403

    upload = req.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"message": "A .numbers file is required"}), 400
    if not upload.filename.lower().endswith(".numbers"):
        return jsonify({"message": "File must be a .numbers spreadsheet"}), 400

    company_id = effective_company_id(req, actor)
    scope = resolve_scope_company_id(req, actor)
    if not can_access_company_scoped(actor, company_id, scope):
        return jsonify({"message": "Forbidden"}), 403

    try:
        parsed = parse_numbers_calendar(upload)
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"message": str(exc)}), 501
    except Exception as exc:
        return jsonify({"message": f"Could not read Numbers file: {exc}"}), 400

    min_event_date = date(date.today().year, 1, 1)

    (
        db.session.query(CalendarEvent)
        .filter(CalendarEvent.company_id == company_id)
        .filter(CalendarEvent.source == "numbers")
        .filter(CalendarEvent.active.is_(True))
        .filter(CalendarEvent.event_date >= min_event_date)
        .update({"active": False}, synchronize_session=False)
    )

    created = []
    for row in parsed:
        if row["event_date"] < min_event_date:
            continue
        event = CalendarEvent(
            company_id=company_id,
            title=row["title"],
            school=row.get("school", ""),
            event_type=row.get("event_type", ""),
            description=_description_from_location(
                row.get("description", ""), row.get("location", "")
            ),
            event_date=row["event_date"],
            num_stations=row.get("num_stations"),
            num_students=row.get("num_students"),
            location=row.get("location", ""),
            created_by_id=actor.user_id,
            source="numbers",
        )
        db.session.add(event)
        created.append(event)

    for event in created:
        sync_calendar_event_to_task(event, actor.user_id)

    db.session.commit()
    generate_calendar_reminders(company_id)
    # generate_shoot_day_reminders(company_id)  # sh/shoot-day-sms-reminders

    return jsonify(
        {
            "message": "calendar synced",
            "results": {
                "imported": len(created),
                "filename": upload.filename,
                "events": calendar_events_schema.dump(created),
            },
        }
    ), 200
