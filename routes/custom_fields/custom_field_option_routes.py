from flask import Blueprint, request

import controllers

custom_field_options = Blueprint("custom_field_options", __name__)


@custom_field_options.route("/custom-field-options", methods=["GET", "POST"])
def custom_field_options_stub():
    return controllers.not_enabled(request)
