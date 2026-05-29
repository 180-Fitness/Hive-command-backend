from uuid import UUID


def validate_uuid4(uuid_string):
    try:
        parsed = UUID(uuid_string, version=4)
    except (ValueError, TypeError, AttributeError):
        return False

    return parsed.hex == uuid_string.replace("-", "")
