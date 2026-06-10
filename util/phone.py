import re


def normalize_phone(phone):
    if phone is None or phone == "":
        return ""
    return re.sub(r"[^0-9]+", "", phone)


# sh/shoot-day-sms-reminders
# def format_e164(phone, default_country_code="1"):
#     digits = normalize_phone(phone)
#     if not digits:
#         return ""
#     if len(digits) == 10:
#         return f"+{default_country_code}{digits}"
#     if len(digits) == 11 and digits.startswith(default_country_code):
#         return f"+{digits}"
#     return f"+{digits}"
