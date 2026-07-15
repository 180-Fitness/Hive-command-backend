from flask import Blueprint, request

import controllers

record_types = Blueprint("record_types", __name__)


@record_types.route("/record-types", methods=["GET", "POST"])
def record_types_stub():
    return controllers.not_enabled(request)
