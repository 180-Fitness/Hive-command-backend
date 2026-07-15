from flask import Blueprint, request

import controllers

custom_field_values = Blueprint("custom_field_values", __name__)


@custom_field_values.route("/custom-field-values", methods=["GET", "POST"])
def custom_field_values_stub():
    return controllers.not_enabled(request)
