from flask import Blueprint, request

import controllers

reports = Blueprint("reports", __name__)


@reports.route("/reports/school-shoot-delivery", methods=["GET"])
def school_shoot_delivery_report_get():
    return controllers.school_shoot_delivery_report_get(request)
