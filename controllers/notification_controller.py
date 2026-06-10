from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.notifications import Notification, notification_schema, notifications_schema
from util.access_control import get_actor, is_admin, resolve_scope_company_id
from util.calendar_reminders import generate_calendar_reminders
# from util.shoot_day_reminders import generate_shoot_day_reminders  # sh/shoot-day-sms-reminders
from util.validate_uuid4 import validate_uuid4


@authenticate_return_auth
def notifications_get(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    if is_admin(actor) and scope:
        generate_calendar_reminders(scope)
        # generate_shoot_day_reminders(scope)  # sh/shoot-day-sms-reminders

    query = (
        db.session.query(Notification)
        .filter(Notification.receiver_id == actor.user_id)
        .order_by(Notification.read.asc(), Notification.created_at.desc())
    )
    if scope:
        query = query.filter(Notification.company_id == scope)

    rows = query.limit(50).all()

    unread_query = db.session.query(Notification).filter(
        Notification.receiver_id == actor.user_id,
        Notification.read.is_(False),
    )
    if scope:
        unread_query = unread_query.filter(Notification.company_id == scope)
    unread = unread_query.count()

    return jsonify(
        {
            "message": "notifications found",
            "results": notifications_schema.dump(rows),
            "unread_count": unread,
        }
    ), 200


@authenticate_return_auth
def notification_mark_read(req: Request, notification_id, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    if not validate_uuid4(notification_id):
        return jsonify({"message": "invalid notification id"}), 404

    notification = (
        db.session.query(Notification)
        .filter(Notification.notification_id == notification_id)
        .filter(Notification.receiver_id == actor.user_id)
        .first()
    )
    if not notification:
        return jsonify({"message": "notification not found"}), 404

    notification.read = True
    db.session.commit()
    return jsonify(
        {"message": "notification updated", "results": notification_schema.dump(notification)}
    ), 200


@authenticate_return_auth
def notifications_mark_all_read(req: Request, auth_info) -> Response:
    actor = get_actor(auth_info)
    if not actor:
        return jsonify({"message": "Unauthorized"}), 401

    scope = resolve_scope_company_id(req, actor)
    query = db.session.query(Notification).filter(
        Notification.receiver_id == actor.user_id,
        Notification.read.is_(False),
    )
    if scope:
        query = query.filter(Notification.company_id == scope)

    query.update({"read": True}, synchronize_session=False)
    db.session.commit()
    return jsonify({"message": "all notifications marked read"}), 200
