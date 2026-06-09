import os
import re
import tempfile
from datetime import date, datetime, timedelta

MONTH_NAMES = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

FALL_PICTURE_DAY = "Fall Picture Day"
RETAKE_FALL_PICTURE_DAY = "Retake Fall Picture Day"

TITLE_KEYS = ("title", "event", "name", "subject")
DATE_KEYS = ("date", "event_date", "when")
MONTH_KEYS = ("month", "mo")
DAY_KEYS = ("day", "dy")
YEAR_KEYS = ("year", "yr")
DESCRIPTION_KEYS = ("description", "desc", "notes", "details", "note")

EXCEL_EPOCH = date(1899, 12, 30)


def _unwrap_cell(value):
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "_value"):
        return value._value
    return value


def _normalize_header(value):
    return re.sub(r"[^a-z0-9]+", "_", str(_unwrap_cell(value) or "").strip().lower()).strip("_")


def _cell_text(value):
    value = _unwrap_cell(value)
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _parse_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().replace(",", "")
    if text.isdigit():
        return int(text)
    return None


def _parse_month(value):
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 12 else None
    if isinstance(value, float):
        month = int(value)
        return month if 1 <= month <= 12 else None
    text = str(value).strip().lower()
    if text.isdigit():
        month = int(text)
        return month if 1 <= month <= 12 else None
    return MONTH_NAMES.get(text)


def _parse_date_value(value):
    value = _unwrap_cell(value)
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, float) and 20000 < value < 80000:
        return EXCEL_EPOCH + timedelta(days=int(value))
    text = str(value).strip()
    if not text:
        return None

    for fmt in (
        "%B %d, %Y",
        "%b %d, %Y",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%B %d %Y",
        "%b %d %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    parts = re.split(r"[/,\-\s]+", text)
    if len(parts) == 3:
        month = _parse_month(parts[0])
        day = _parse_int(parts[1])
        year = _parse_int(parts[2])
        if month and day and year:
            if year < 100:
                year += 2000
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


def _pick_column(headers, keys):
    for key in keys:
        if key in headers:
            return headers[key]
    return None


def _cell_at(row, index):
    if index is None or index >= len(row):
        return None
    return row[index]


def _find_school_schedule_columns(headers):
    cols = {}
    for key, index in headers.items():
        if key in ("schools", "school"):
            cols["school"] = index
        elif "retake" in key and "picture" in key:
            cols["retake_date"] = index
        elif "fall" in key and "picture" in key:
            cols["fall_date"] = index
        elif "station" in key:
            cols["stations"] = index
        elif "student" in key:
            cols["students"] = index
        elif "location" in key:
            cols["location"] = index
    return cols


def _is_school_schedule(headers):
    cols = _find_school_schedule_columns(headers)
    return cols.get("school") is not None and (
        cols.get("fall_date") is not None or cols.get("retake_date") is not None
    )


def _build_school_event(school, event_type, event_date, stations, students, location):
    location = (location or "").strip()
    return {
        "school": school,
        "event_type": event_type,
        "title": f"{school} — {event_type}",
        "event_date": event_date,
        "num_stations": stations,
        "num_students": students,
        "location": location,
        "description": location,
    }


def _row_to_school_events(row, cols):
    school = _cell_text(_cell_at(row, cols.get("school")))
    if not school:
        return []

    stations = _parse_int(_cell_at(row, cols.get("stations")))
    students = _parse_int(_cell_at(row, cols.get("students")))
    location = _cell_text(_cell_at(row, cols.get("location")))

    events = []
    fall_date = _parse_date_value(_cell_at(row, cols.get("fall_date")))
    if fall_date:
        events.append(
            _build_school_event(
                school, FALL_PICTURE_DAY, fall_date, stations, students, location
            )
        )

    retake_date = _parse_date_value(_cell_at(row, cols.get("retake_date")))
    if retake_date:
        events.append(
            _build_school_event(
                school, RETAKE_FALL_PICTURE_DAY, retake_date, stations, students, location
            )
        )

    return events


def _row_to_generic_event(row, column_indexes):
    title_idx = column_indexes.get("title")
    if title_idx is None:
        return None

    title = _cell_text(row[title_idx] if title_idx < len(row) else None)
    if not title:
        return None

    event_date = None
    date_idx = column_indexes.get("date")
    if date_idx is not None and date_idx < len(row):
        event_date = _parse_date_value(row[date_idx])

    if event_date is None:
        month_idx = column_indexes.get("month")
        day_idx = column_indexes.get("day")
        year_idx = column_indexes.get("year")
        if month_idx is None or day_idx is None or year_idx is None:
            return None
        month = _parse_month(row[month_idx] if month_idx < len(row) else None)
        day = _parse_int(row[day_idx] if day_idx < len(row) else None)
        year = _parse_int(row[year_idx] if year_idx < len(row) else None)
        if not month or not day or not year:
            return None
        if year < 100:
            year += 2000
        try:
            event_date = date(year, month, day)
        except ValueError:
            return None

    description = ""
    desc_idx = column_indexes.get("description")
    if desc_idx is not None and desc_idx < len(row):
        description = _cell_text(row[desc_idx])

    return {
        "title": title,
        "school": title,
        "event_type": "",
        "description": description,
        "event_date": event_date,
        "num_stations": None,
        "num_students": None,
        "location": "",
    }


def parse_event_date_from_payload(payload):
    if payload.get("event_date"):
        parsed = _parse_date_value(payload.get("event_date"))
        if parsed:
            return parsed

    month = _parse_month(payload.get("month"))
    day = _parse_int(payload.get("day"))
    year = _parse_int(payload.get("year"))
    if not month or not day or not year:
        return None
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _headers_from_row(row):
    headers = {}
    for index, cell in enumerate(row):
        key = _normalize_header(cell)
        if key:
            headers[key] = index
    return headers


def _find_header_row_index(rows):
    for index, row in enumerate(rows[:10]):
        keys = [_normalize_header(cell) for cell in row if cell is not None]
        if any(key in ("schools", "school") for key in keys if key):
            return index
    return 0


def _parse_school_rows(rows):
    if not rows:
        return []

    header_idx = _find_header_row_index(rows)
    headers = _headers_from_row(rows[header_idx])
    if not _is_school_schedule(headers):
        return []

    cols = _find_school_schedule_columns(headers)
    events = []
    for row in rows[header_idx + 1 :]:
        if not row or all(
            _unwrap_cell(cell) is None or str(_unwrap_cell(cell)).strip() == ""
            for cell in row
        ):
            continue
        events.extend(_row_to_school_events(row, cols))
    return events


def _document_path(source):
    """numbers-parser requires a file path — save uploads to a temp file."""
    if isinstance(source, (str, os.PathLike)):
        return str(source), None

    fd, temp_path = tempfile.mkstemp(suffix=".numbers")
    os.close(fd)

    if hasattr(source, "save"):
        source.save(temp_path)
    elif hasattr(source, "read"):
        with open(temp_path, "wb") as handle:
            handle.write(source.read())
    else:
        os.remove(temp_path)
        raise ValueError("Unsupported Numbers file upload")

    return temp_path, temp_path


def parse_numbers_calendar(source):
    """Parse a .numbers file into calendar event dicts."""
    try:
        from numbers_parser import Document
    except ImportError as exc:
        raise RuntimeError(
            "numbers-parser is not installed on the server. "
            "Install it with: pip install numbers-parser"
        ) from exc

    path, temp_path = _document_path(source)
    try:
        doc = Document(path)
        if not doc.sheets:
            raise ValueError("The Numbers file has no sheets")

        events = []
        seen_headers = []
        for sheet in doc.sheets:
            for table in sheet.tables:
                rows = list(table.rows(values_only=True))
                if not rows:
                    continue
                header_idx = _find_header_row_index(rows)
                headers = _headers_from_row(rows[header_idx])
                seen_headers.append(", ".join(sorted(headers.keys())))
                events.extend(_parse_school_rows(rows))

        if events:
            return events

        header_hint = seen_headers[0] if seen_headers else "none"
        raise ValueError(
            "Could not find school picture day rows. Expected columns: Schools, "
            "Fall Picture Day, Retake Fall Picture Day, # of Stations, "
            f"# of Students, Location. Found: {header_hint}"
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
