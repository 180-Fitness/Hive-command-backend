from flask import Blueprint, request

import controllers

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/dashboard/auth", methods=["POST"])
def dashboard_auth_add():
    return controllers.dashboard_auth_add(request)


@dashboard.route("/dashboard/check-login", methods=["GET"])
def dashboard_auth_check_login():
    return controllers.dashboard_auth_check_login(request)


@dashboard.route("/dashboard/logout", methods=["PUT"])
def dashboard_auth_logout():
    return controllers.dashboard_auth_logout(request)


@dashboard.route("/dashboard/week-summary", methods=["GET"])
def dashboard_week_summary_get():
    return controllers.dashboard_week_summary_get(request)
