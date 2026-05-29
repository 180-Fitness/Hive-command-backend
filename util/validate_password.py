import re


def validate_password(password):
    if not password or len(password) < 8:
        return False

    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))

    return has_upper and has_lower and has_digit
