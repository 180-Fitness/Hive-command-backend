from flask import Blueprint, request

import controllers

export_data = Blueprint("export_data", __name__)


@export_data.route("/export", methods=["GET"])
def export_stub():
    return controllers.not_enabled(request)
