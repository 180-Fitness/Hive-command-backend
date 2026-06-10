import csv
import io
import os
import re
from datetime import datetime, timezone
import config
from db import db
from models.app_users import AppUser
from models.companies import Company
from models.order_lines import OrderLine
from models.projects import Project
from models.task_statuses import TaskStatus
from models.tasks import Task
from util.company_workflow import company_by_id


YEAR_SUFFIX_RE = re.compile(r"\s+20\d{2}$")
YEAR_EXTRACT_RE = re.compile(r"(20\d{2})$")
SCHOOL_TOKEN_RE = re.compile(r"^school\s+", re.IGNORECASE)

FIELD_ALIASES = {
    "order": "order_number",
    "order_number": "order_number",
    "billfirstname": "bill_first_name",
    "bill_first_name": "bill_first_name",
    "billlastname": "bill_last_name",
    "bill_last_name": "bill_last_name",
    "billemail": "bill_email",
    "bill_email": "bill_email",
    "billmobile": "bill_mobile",
    "bill_mobile": "bill_mobile",
    "address1": "address1",
    "address2": "address2",
    "city": "city",
    "state": "state",
    "zip": "zip",
    "eventname": "event_name",
    "event_name": "event_name",
    "productname": "product_name",
    "product_name": "product_name",
    "quantity": "quantity",
    "images": "images",
    "options": "options",
    "notes": "notes",
    "subject": "subject",
}


def _sync_config(company):
    if not company:
        return {}
    return config.proofpix_order_sync.get(company.name, {})


def _normalize_text(value):
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def _normalize_header(value):
    key = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return FIELD_ALIASES.get(key, key)


def _strip_trailing_year(value, enabled=True):
    text = (value or "").strip()
    if not enabled or not text:
        return text
    return YEAR_SUFFIX_RE.sub("", text).strip()


def _extract_trailing_year(event_name):
    match = YEAR_EXTRACT_RE.search((event_name or "").strip())
    return match.group(1) if match else None


def _cell_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _parse_quantity(value):
    text = _cell_text(value)
    if not text:
        return 1
    try:
        parsed = int(float(text))
        return parsed if parsed > 0 else 1
    except (TypeError, ValueError):
        return 1


def _build_description(row):
    parts = []
    notes = _cell_text(row.get("notes"))
    first = _cell_text(row.get("bill_first_name"))
    last = _cell_text(row.get("bill_last_name"))
    email = _cell_text(row.get("bill_email"))
    mobile = _cell_text(row.get("bill_mobile"))
    options = _cell_text(row.get("options"))

    if notes:
        parts.append(f"Notes: {notes}")
    contact = " ".join(part for part in [first, last] if part).strip()
    if contact:
        parts.append(f"Contact: {contact}")
    if email:
        parts.append(f"Email: {email}")
    if mobile:
        parts.append(f"Mobile: {mobile}")
    if options:
        parts.append(f"Options: {options}")
    return "\n".join(parts)


def _read_csv_text(upload):
    raw = upload.read()
    if isinstance(raw, bytes):
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    return raw


def parse_proofpix_csv(source):
    if isinstance(source, (str, os.PathLike)):
        with open(source, "rb") as handle:
            return parse_proofpix_csv(handle)

    text = _read_csv_text(source)
    if not text.strip():
        raise ValueError("CSV file is empty")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV file has no header row")

    column_map = {_normalize_header(name): name for name in reader.fieldnames if name}
    if "event_name" not in column_map:
        raise ValueError("CSV must include an EventName column")

    rows = []
    for index, raw_row in enumerate(reader, start=2):
        if not raw_row or not any(_cell_text(value) for value in raw_row.values()):
            continue

        row = {}
        for key, source_key in column_map.items():
            row[key] = _cell_text(raw_row.get(source_key))
        row["_line_number"] = index
        rows.append(row)

    if not rows:
        raise ValueError("CSV file has no data rows")
    return rows


def _alias_map(sync_cfg):
    aliases = {}
    for event_name, task_name in (sync_cfg.get("event_aliases") or {}).items():
        aliases[_normalize_text(event_name)] = (task_name or "").strip()
    return aliases


def _find_project(company_id, event_name):
    normalized_event = _normalize_text(event_name)
    projects = (
        db.session.query(Project)
        .filter(Project.company_id == company_id)
        .filter(Project.active.is_(True))
        .all()
    )

    best = None
    best_len = 0
    for project in projects:
        project_name = _normalize_text(project.name)
        if not project_name:
            continue
        if normalized_event == project_name or normalized_event.startswith(f"{project_name} "):
            if len(project_name) > best_len:
                best = project
                best_len = len(project_name)
    return best


def _shoot_part(event_name, project_name, strip_year):
    remainder = (event_name or "").strip()
    if project_name:
        pattern = re.compile(re.escape(project_name.strip()), re.IGNORECASE)
        remainder = pattern.sub("", remainder, count=1).strip()
    remainder = _strip_trailing_year(remainder, strip_year)
    remainder = SCHOOL_TOKEN_RE.sub("", remainder).strip(" -–—")
    return remainder


def _proposed_task_name(event_name, project, sync_cfg, alias_target=None):
    if alias_target:
        return alias_target

    shoot_part = _shoot_part(
        event_name,
        project.name if project else "",
        sync_cfg.get("strip_trailing_year", True),
    )
    if not shoot_part:
        return (sync_cfg.get("default_shoot_task_name") or event_name).strip()

    year = _extract_trailing_year(event_name)
    if year and year not in shoot_part:
        return f"{shoot_part} {year}"
    return shoot_part


def _task_match_score(task_name, shoot_part):
    task_norm = _normalize_text(task_name)
    shoot_norm = _normalize_text(shoot_part)
    if not task_norm or not shoot_norm:
        return 0
    if task_norm == shoot_norm:
        return 100
    if shoot_norm in task_norm or task_norm in shoot_norm:
        return 80 + min(len(shoot_norm), len(task_norm))
    return 0


def _import_actor_id(company_id):
    admin = (
        db.session.query(AppUser)
        .filter(AppUser.email == config.admin_email)
        .filter(AppUser.active.is_(True))
        .first()
    )
    if admin:
        return admin.user_id

    fallback = (
        db.session.query(AppUser)
        .filter(AppUser.company_id == company_id)
        .filter(AppUser.active.is_(True))
        .first()
    )
    return fallback.user_id if fallback else None


def _default_task_status(company_id, sync_cfg):
    status_name = sync_cfg.get("new_task_status", config.SCHOOL_PICTURE_STAGE_PRINT)
    return (
        db.session.query(TaskStatus)
        .filter(TaskStatus.company_id == company_id)
        .filter(TaskStatus.name == status_name)
        .first()
    )


def _find_task_by_name(company_id, project_id, task_name):
    return (
        db.session.query(Task)
        .filter(Task.company_id == company_id)
        .filter(Task.project_id == project_id)
        .filter(Task.active.is_(True))
        .filter(Task.name == task_name)
        .first()
    )


def _create_task(company_id, project_id, task_name, sync_cfg, created_by_id, event_name):
    status = _default_task_status(company_id, sync_cfg)
    if not status:
        return None, "missing task status for new shoot tasks"

    if not created_by_id:
        return None, "no import user available to create tasks"

    description = f"Proof Pix orders\nEvent: {event_name}"
    task = Task(
        company_id=company_id,
        name=task_name,
        task_status_id=status.task_status_id,
        created_by_id=created_by_id,
        description=description,
        project_id=project_id,
    )
    db.session.add(task)
    db.session.flush()
    return task, None


def resolve_or_create_task_for_event(
    company_id,
    event_name,
    sync_cfg=None,
    *,
    create_if_missing=False,
    created_by_id=None,
):
    company = company_by_id(company_id)
    sync_cfg = sync_cfg if sync_cfg is not None else _sync_config(company)
    event_name = (event_name or "").strip()
    if not event_name:
        return None, False, "missing EventName"

    created = False
    aliases = _alias_map(sync_cfg)
    alias_target = aliases.get(_normalize_text(event_name))

    project = _find_project(company_id, event_name)
    if not project:
        return None, False, "no matching school project"

    if alias_target:
        task = _find_task_by_name(company_id, project.project_id, alias_target)
        if task:
            return task, False, None
        if create_if_missing and sync_cfg.get("create_tasks_on_import", True):
            task, reason = _create_task(
                company_id,
                project.project_id,
                alias_target,
                sync_cfg,
                created_by_id,
                event_name,
            )
            if task:
                return task, True, None
            return None, False, reason
        return None, False, f"alias maps to missing task '{alias_target}'"

    shoot_part = _shoot_part(
        event_name,
        project.name,
        sync_cfg.get("strip_trailing_year", True),
    )
    if not shoot_part:
        return None, False, "EventName matches school only — add an alias for the shoot task"

    tasks = (
        db.session.query(Task)
        .filter(Task.company_id == company_id)
        .filter(Task.project_id == project.project_id)
        .filter(Task.active.is_(True))
        .all()
    )

    scored = []
    for task in tasks:
        score = _task_match_score(task.name, shoot_part)
        if score > 0:
            scored.append((score, task))

    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        best_score = scored[0][0]
        top = [task for score, task in scored if score == best_score]
        if len(top) > 1:
            names = ", ".join(task.name for task in top)
            return None, False, f"ambiguous task match ({names}) — add an alias"
        return top[0], False, None

    if not create_if_missing or not sync_cfg.get("create_tasks_on_import", True):
        return None, False, f"no task matches shoot '{shoot_part}' under {project.name}"

    task_name = _proposed_task_name(event_name, project, sync_cfg)
    existing = _find_task_by_name(company_id, project.project_id, task_name)
    if existing:
        return existing, False, None

    task, reason = _create_task(
        company_id,
        project.project_id,
        task_name,
        sync_cfg,
        created_by_id,
        event_name,
    )
    if task:
        return task, True, None
    return None, False, reason


def resolve_task_for_event(company_id, event_name, sync_cfg=None):
    task, _, reason = resolve_or_create_task_for_event(
        company_id,
        event_name,
        sync_cfg,
        create_if_missing=False,
    )
    return task, reason


def _dedup_key(order_number, product_name, images):
    return (
        _normalize_text(order_number),
        _normalize_text(product_name),
        _normalize_text(images),
    )


def _find_existing_line(task_id, order_number, product_name, images):
    order_key, product_key, image_key = _dedup_key(order_number, product_name, images)
    lines = (
        db.session.query(OrderLine)
        .filter(OrderLine.task_id == task_id)
        .filter(OrderLine.active.is_(True))
        .all()
    )
    for line in lines:
        if _dedup_key(line.proofpix_order_number, line.product_name, line.images) == (
            order_key,
            product_key,
            image_key,
        ):
            return line
    return None


def _apply_row_to_line(line, row):
    line.event_name = _cell_text(row.get("event_name"))
    line.bill_first_name = _cell_text(row.get("bill_first_name"))
    line.bill_last_name = _cell_text(row.get("bill_last_name"))
    line.student_name = _cell_text(row.get("subject"))
    line.product_name = _cell_text(row.get("product_name"))
    line.quantity = _parse_quantity(row.get("quantity"))
    line.images = _cell_text(row.get("images"))
    line.ship_address1 = _cell_text(row.get("address1"))
    line.ship_address2 = _cell_text(row.get("address2"))
    line.ship_city = _cell_text(row.get("city"))
    line.ship_state = _cell_text(row.get("state"))
    line.ship_zip = _cell_text(row.get("zip"))
    line.description = _build_description(row)
    line.updated_at = datetime.now(timezone.utc)


def import_proofpix_orders(company_id, rows, *, create_tasks=True):
    company = company_by_id(company_id)
    sync_cfg = _sync_config(company)
    created_by_id = _import_actor_id(company_id) if create_tasks else None

    imported = 0
    updated = 0
    tasks_created = 0
    unmatched = []
    task_cache = {}

    for row in rows:
        event_name = _cell_text(row.get("event_name"))
        order_number = _cell_text(row.get("order_number"))
        product_name = _cell_text(row.get("product_name"))
        images = _cell_text(row.get("images"))
        line_number = row.get("_line_number")

        cache_key = _normalize_text(event_name)
        if cache_key in task_cache:
            task, reason = task_cache[cache_key]
        else:
            task, task_was_created, reason = resolve_or_create_task_for_event(
                company_id,
                event_name,
                sync_cfg,
                create_if_missing=create_tasks,
                created_by_id=created_by_id,
            )
            task_cache[cache_key] = (task, reason)
            if task_was_created:
                tasks_created += 1

        if not task:
            unmatched.append(
                {
                    "line": line_number,
                    "event_name": event_name,
                    "order_number": order_number,
                    "reason": reason,
                }
            )
            continue

        existing = _find_existing_line(task.task_id, order_number, product_name, images)
        if existing:
            _apply_row_to_line(existing, row)
            updated += 1
            continue

        line = OrderLine(
            company_id=company_id,
            task_id=task.task_id,
            proofpix_order_number=order_number,
            event_name=event_name,
            bill_first_name=_cell_text(row.get("bill_first_name")),
            bill_last_name=_cell_text(row.get("bill_last_name")),
            student_name=_cell_text(row.get("subject")),
            product_name=product_name,
            quantity=_parse_quantity(row.get("quantity")),
            images=images,
            ship_address1=_cell_text(row.get("address1")),
            ship_address2=_cell_text(row.get("address2")),
            ship_city=_cell_text(row.get("city")),
            ship_state=_cell_text(row.get("state")),
            ship_zip=_cell_text(row.get("zip")),
            description=_build_description(row),
        )
        db.session.add(line)
        imported += 1

    db.session.commit()
    return {
        "imported": imported,
        "updated": updated,
        "tasks_created": tasks_created,
        "unmatched": unmatched,
        "total_rows": len(rows),
    }


def company_by_name(name):
    return (
        db.session.query(Company)
        .filter(Company.active.is_(True))
        .filter(Company.name == name)
        .first()
    )
