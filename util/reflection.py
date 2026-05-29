from flask import jsonify


def populate_object(instance, payload):
    for field in payload.keys():
        if not hasattr(instance, field):
            return jsonify({"error": f"Unknown field: {field}"}), 400
        setattr(instance, field, payload[field])

    return None
