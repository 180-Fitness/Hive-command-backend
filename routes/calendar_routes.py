from flask import Blueprint, request

import controllers

calendar = Blueprint("calendar", __name__)


@calendar.route("/calendar/events", methods=["GET"])
def calendar_events_get():
    return controllers.calendar_events_get(request)


@calendar.route("/calendar/event/<event_id>", methods=["GET"])
def calendar_event_get_by_id(event_id):
    return controllers.calendar_event_get_by_id(request, event_id)


@calendar.route("/calendar/event", methods=["POST"])
def calendar_event_add():
    return controllers.calendar_event_add(request)


@calendar.route("/calendar/event/<event_id>", methods=["PUT"])
def calendar_event_update(event_id):
    return controllers.calendar_event_update(request, event_id)


@calendar.route("/calendar/event/<event_id>", methods=["DELETE"])
def calendar_event_delete(event_id):
    return controllers.calendar_event_delete(request, event_id)


@calendar.route("/calendar/sync", methods=["POST"])
def calendar_sync_numbers():
    return controllers.calendar_sync_numbers(request)
