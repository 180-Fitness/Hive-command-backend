from flask import Blueprint, request

import controllers

clients = Blueprint("clients", __name__)


@clients.route("/clients", methods=["GET", "POST"])
@clients.route("/client/<path:_id>", methods=["GET", "PUT", "DELETE"])
def clients_stub(_id=None):
    return controllers.not_enabled(request)
