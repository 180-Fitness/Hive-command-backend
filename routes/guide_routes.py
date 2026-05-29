from flask import Blueprint, request

import controllers

guides = Blueprint("guides", __name__)


@guides.route("/guides", methods=["GET"])
def guides_get():
    return controllers.guides_get(request)


@guides.route("/guides/admin", methods=["GET"])
def guides_admin_get():
    return controllers.guides_admin_get(request)


@guides.route("/guide/<guide_id>", methods=["GET"])
def guide_get_by_id(guide_id):
    return controllers.guide_get_by_id(request, guide_id)


@guides.route("/guide", methods=["POST"])
def guide_add():
    return controllers.guide_add(request)


@guides.route("/guide/<guide_id>", methods=["PUT"])
def guide_update(guide_id):
    return controllers.guide_update(request, guide_id)


@guides.route("/guide/<guide_id>", methods=["DELETE"])
def guide_delete(guide_id):
    return controllers.guide_delete(request, guide_id)
