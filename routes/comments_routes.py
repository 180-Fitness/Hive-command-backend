from flask import Blueprint, request

import controllers

comments = Blueprint("comments", __name__)


@comments.route("/comments/task/<task_id>", methods=["GET"])
def comments_get_by_task(task_id):
    return controllers.comments_get_by_task(request, task_id)


@comments.route("/comment", methods=["POST"])
def comment_add():
    return controllers.comment_add(request)


@comments.route("/comment/<comment_id>", methods=["PUT"])
def comment_update(comment_id):
    return controllers.comment_update(request, comment_id)


@comments.route("/comment/delete/<comment_id>", methods=["DELETE"])
def comment_delete(comment_id):
    return controllers.comment_delete(request, comment_id)
