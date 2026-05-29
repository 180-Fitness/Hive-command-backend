from flask import Blueprint, request

import controllers

projects = Blueprint("projects", __name__)


@projects.route("/projects", methods=["GET"])
def projects_get():
    return controllers.projects_get(request)


@projects.route("/project/<project_id>", methods=["GET"])
def project_get_by_id(project_id):
    return controllers.project_get_by_id(request, project_id)


@projects.route("/project", methods=["POST"])
def project_add():
    return controllers.project_add(request)


@projects.route("/project/<project_id>", methods=["PUT"])
def project_update(project_id):
    return controllers.project_update(request, project_id)


@projects.route("/project/<project_id>", methods=["DELETE"])
def project_delete(project_id):
    return controllers.project_delete(request, project_id)
