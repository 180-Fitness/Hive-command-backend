from flask import Blueprint

import controllers

notifications = Blueprint("notifications", __name__)


@notifications.route("/notifications", methods=["GET"])
@notifications.route("/notification/<path:_id>", methods=["PUT", "DELETE"])
def notifications_stub(_id=None):
    return controllers.not_enabled()
