from flask import jsonify


def not_enabled():
    return jsonify(
        {
            "message": "This capability is not enabled for Hive Command private deployments.",
        }
    ), 501
