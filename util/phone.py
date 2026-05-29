import re


def normalize_phone(phone):
    if phone is None or phone == "":
        return ""
    return re.sub(r"[^0-9]+", "", phone)
