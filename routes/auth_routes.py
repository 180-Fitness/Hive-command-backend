from flask import Blueprint, Response, request

import controllers

auth = Blueprint("auth", __name__)


@auth.route("/user/auth", methods=["POST"])
def auth_token_add() -> Response:
    return controllers.auth_token_add(request)


@auth.route("/user/logout", methods=["PUT"])
def auth_token_remove() -> Response:
    return controllers.auth_token_remove(request)


@auth.route("/user/token_removal", methods=["DELETE"])
def auth_token_remove_expired() -> Response:
    return controllers.auth_token_remove_expired(request)


@auth.route("/check-login", methods=["GET"])
def auth_check_login() -> Response:
    return controllers.auth_check_login(request)
