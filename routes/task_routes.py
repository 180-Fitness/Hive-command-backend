from flask import Blueprint, request

import controllers

tasks = Blueprint("tasks", __name__)


@tasks.route("/tasks/backlog", methods=["GET"])
def tasks_backlog_get():
    return controllers.tasks_backlog_get(request)


@tasks.route("/tasks/me", methods=["GET"])
def tasks_my_get():
    return controllers.tasks_my_get(request)


@tasks.route("/tasks", methods=["GET"])
def tasks_get():
    return controllers.tasks_get(request)


@tasks.route("/task/<task_id>", methods=["GET"])
def task_get_by_id(task_id):
    return controllers.task_get_by_id(request, task_id)


@tasks.route("/task", methods=["POST"])
def task_add():
    return controllers.task_add(request)


@tasks.route("/task/<task_id>", methods=["PUT"])
def task_update(task_id):
    return controllers.task_update(request, task_id)
