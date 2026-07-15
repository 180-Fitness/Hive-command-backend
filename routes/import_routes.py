from flask import Blueprint, request

import controllers

import_data = Blueprint("import_data", __name__)


@import_data.route("/import", methods=["POST"])
def import_stub():
    return controllers.not_enabled(request)
