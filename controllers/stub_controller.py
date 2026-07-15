from flask import jsonify

from lib.authenticate import authenticate


@authenticate
def not_enabled(req):
    return jsonify(
        {
            "message": "This capability is not enabled for Hive Command private deployments.",
        }
    ), 501
