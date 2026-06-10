from flask import Blueprint, request

import controllers

notifications = Blueprint("notifications", __name__)


@notifications.route("/notifications", methods=["GET"])
def notifications_get():
    return controllers.notifications_get(request)


@notifications.route("/notifications/read-all", methods=["PATCH"])
def notifications_mark_all_read():
    return controllers.notifications_mark_all_read(request)


@notifications.route("/notification/<notification_id>/read", methods=["PATCH"])
def notification_mark_read(notification_id):
    return controllers.notification_mark_read(request, notification_id)
