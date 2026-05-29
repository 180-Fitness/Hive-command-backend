from flask import Blueprint, request

import controllers

task_statuses = Blueprint("task_statuses", __name__)


@task_statuses.route("/task-statuses", methods=["GET"])
def task_statuses_get():
    return controllers.task_statuses_get(request)


@task_statuses.route("/task-status", methods=["POST"])
def task_status_add():
    return controllers.task_status_add(request)


@task_statuses.route("/task-status/<task_status_id>", methods=["PUT"])
def task_status_update(task_status_id):
    return controllers.task_status_update(request, task_status_id)
