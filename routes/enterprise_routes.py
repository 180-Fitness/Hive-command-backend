from flask import Blueprint, request

import controllers

enterprise = Blueprint("enterprise", __name__)


@enterprise.route("/enterprise", methods=["GET"])
def enterprise_get():
    return controllers.enterprise_get(request)
