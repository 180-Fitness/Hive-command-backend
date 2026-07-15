from flask import Blueprint, request

import controllers

custom_fields = Blueprint("custom_fields", __name__)


@custom_fields.route("/custom-fields", methods=["GET", "POST"])
def custom_fields_stub():
    return controllers.not_enabled(request)
