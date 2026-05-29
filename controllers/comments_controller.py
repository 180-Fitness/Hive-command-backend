from flask import Request, Response, jsonify

from db import db
from lib.authenticate import authenticate_return_auth
from models.comments import Comment, comment_detail_schema, comments_detail_schema
from models.tasks import Task
from util.access_control import can_access_company
from util.reflection import populate_object
from util.validate_uuid4 import validate_uuid4


def _task_for_comment(task_id, auth_info):
    if not validate_uuid4(task_id):
        return None, (jsonify({"message": "invalid task id"}), 404)

    task = db.session.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        return None, (jsonify({"message": "task not found"}), 404)

    if not can_access_company(auth_info.user, task.company_id):
        return None, (jsonify({"message": "Forbidden"}), 403)

    return task, None


def _comment_with_access(comment_id, auth_info):
    if not validate_uuid4(comment_id):
        return None, (jsonify({"message": "invalid comment id"}), 404)

    comment = db.session.query(Comment).filter(Comment.comment_id == comment_id).first()
    if not comment:
        return None, (jsonify({"message": "comment not found"}), 404)

    if not can_access_company(auth_info.user, comment.task.company_id):
        return None, (jsonify({"message": "Forbidden"}), 403)

    return comment, None


@authenticate_return_auth
def comments_get_by_task(req: Request, task_id, auth_info) -> Response:
    task, error = _task_for_comment(task_id, auth_info)
    if error:
        return error

    comments = (
        db.session.query(Comment)
        .filter(Comment.task_id == task.task_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    return (
        jsonify(
            {
                "message": "comments found",
                "results": comments_detail_schema.dump(comments),
            }
        ),
        200,
    )


@authenticate_return_auth
def comment_add(req: Request, auth_info) -> Response:
    payload = req.get_json() or {}
    task_id = payload.get("task_id")

    task, error = _task_for_comment(task_id, auth_info)
    if error:
        return error

    body = (payload.get("body") or "").strip()
    if not body:
        return jsonify({"message": "comment body is required"}), 400

    comment = Comment(
        task_id=task.task_id,
        user_id=auth_info.user_id,
        body=body,
    )
    db.session.add(comment)
    db.session.commit()

    return (
        jsonify(
            {"message": "comment added", "results": comment_detail_schema.dump(comment)}
        ),
        201,
    )


@authenticate_return_auth
def comment_update(req: Request, comment_id, auth_info) -> Response:
    comment, error = _comment_with_access(comment_id, auth_info)
    if error:
        return error

    if comment.user_id != auth_info.user_id:
        return jsonify({"message": "Forbidden"}), 403

    payload = req.get_json() or {}
    if "comment_id" in payload:
        return jsonify({"message": "cannot update comment id"}), 400

    body = (payload.get("body") or "").strip()
    if not body:
        return jsonify({"message": "comment body is required"}), 400

    comment.body = body
    db.session.commit()

    return (
        jsonify(
            {"message": "comment updated", "results": comment_detail_schema.dump(comment)}
        ),
        200,
    )


@authenticate_return_auth
def comment_delete(req: Request, comment_id, auth_info) -> Response:
    comment, error = _comment_with_access(comment_id, auth_info)
    if error:
        return error

    if comment.user_id != auth_info.user_id and auth_info.user.role not in (
        "company_admin",
        "enterprise_admin",
    ):
        return jsonify({"message": "Forbidden"}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"message": "comment deleted"}), 200
