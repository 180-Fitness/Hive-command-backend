from flask import Blueprint, request

import controllers

app_users = Blueprint("app_users", __name__)


@app_users.route("/users", methods=["GET"])
def users_get_all():
    return controllers.users_get_all(request)


@app_users.route("/users/assignees", methods=["GET"])
def users_assignees_get():
    return controllers.users_assignees_get(request)


@app_users.route("/user/<user_id>", methods=["GET"])
def user_get_by_id(user_id):
    return controllers.user_get_by_id(request, user_id)


@app_users.route("/user/me", methods=["GET"])
def user_get_me():
    return controllers.user_get_me(request)


@app_users.route("/users/company/<company_id>", methods=["GET"])
def users_get_by_company(company_id):
    return controllers.users_get_by_company(request, company_id)


@app_users.route("/user", methods=["POST"])
def user_add():
    return controllers.user_add(request)


@app_users.route("/user/<user_id>", methods=["PUT"])
def user_update(user_id):
    return controllers.user_update(request, user_id)


@app_users.route("/user/status/<user_id>", methods=["PATCH"])
def user_set_active(user_id):
    return controllers.user_set_active(request, user_id)


@app_users.route("/user/verify-password", methods=["POST"])
def user_verify_password():
    return controllers.user_verify_password(request)
