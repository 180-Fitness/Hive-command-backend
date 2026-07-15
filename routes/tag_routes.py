from flask import Blueprint, request

import controllers

tags = Blueprint("tags", __name__)


@tags.route("/tags", methods=["GET", "POST"])
@tags.route("/tag/<path:_id>", methods=["GET", "PUT", "DELETE"])
def tags_stub(_id=None):
    return controllers.not_enabled(request)
