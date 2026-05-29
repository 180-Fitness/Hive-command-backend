from datetime import datetime


def check_health():
    return (
        f"<html><body><div>Hive backend healthy at {datetime.now()}</div></body></html>",
        200,
    )
