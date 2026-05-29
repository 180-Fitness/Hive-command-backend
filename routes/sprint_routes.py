from flask import Blueprint, request

import controllers

sprints = Blueprint("sprints", __name__)


@sprints.route("/sprints", methods=["GET"])
def sprints_get():
    return controllers.sprints_get(request)


@sprints.route("/sprints", methods=["POST"])
def sprint_add():
    return controllers.sprint_add(request)


@sprints.route("/sprint/<sprint_id>", methods=["GET"])
def sprint_get_by_id(sprint_id):
    return controllers.sprint_get_by_id(request, sprint_id)


@sprints.route("/sprint/<sprint_id>", methods=["PUT"])
def sprint_update(sprint_id):
    return controllers.sprint_update(request, sprint_id)


@sprints.route("/sprint/<sprint_id>", methods=["DELETE"])
def sprint_delete(sprint_id):
    return controllers.sprint_delete(request, sprint_id)
