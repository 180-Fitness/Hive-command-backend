from flask import jsonify


def populate_object(instance, payload, allowed_fields=None):
    """Set attributes from payload.

    When allowed_fields is provided, only those keys may be set (mass-assignment guard).
    """
    for field in payload.keys():
        if allowed_fields is not None and field not in allowed_fields:
            return jsonify({"error": f"Field not allowed: {field}"}), 400
        if not hasattr(instance, field):
            return jsonify({"error": f"Unknown field: {field}"}), 400
        setattr(instance, field, payload[field])

    return None
