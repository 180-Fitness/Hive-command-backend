from flask import Blueprint, request

import controllers

search = Blueprint("search", __name__)


@search.route("/search", methods=["GET"])
def search_stub():
    return controllers.not_enabled(request)
