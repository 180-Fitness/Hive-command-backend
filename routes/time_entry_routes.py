from flask import Blueprint

import controllers

time_entries = Blueprint("time_entries", __name__)


@time_entries.route("/time-entries", methods=["GET", "POST"])
@time_entries.route("/time-entry/<path:_id>", methods=["GET", "PUT", "DELETE"])
def time_entries_stub(_id=None):
    return controllers.not_enabled()
