from flask import Blueprint, request

import controllers

companies = Blueprint("companies", __name__)


@companies.route("/companies", methods=["GET"])
def companies_get():
    return controllers.companies_get(request)


@companies.route("/company/<company_id>", methods=["GET"])
def company_get_by_id(company_id):
    return controllers.company_get_by_id(request, company_id)


@companies.route("/company", methods=["POST"])
def company_add():
    return controllers.company_add(request)


@companies.route("/company/<company_id>", methods=["PUT"])
def company_update(company_id):
    return controllers.company_update(request, company_id)


@companies.route("/company/status/<company_id>", methods=["PATCH"])
def company_set_active(company_id):
    return controllers.company_set_active(request, company_id)
