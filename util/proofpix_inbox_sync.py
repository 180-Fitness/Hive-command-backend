import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from util.company_workflow import company_by_id
from util.proofpix_order_sync import company_by_name, import_proofpix_orders, parse_proofpix_csv


def _inbox_config():
    import config

    return getattr(config, "proofpix_inbox", {})


def resolve_inbox_path():
    cfg = _inbox_config()
    raw = os.getenv("PROOFPIX_INBOX_PATH", cfg.get("path", "")).strip()
    if not raw:
        return None
    return Path(os.path.expanduser(raw)).resolve()


def resolve_inbox_company_id():
    cfg = _inbox_config()
    company_name = os.getenv("PROOFPIX_INBOX_COMPANY", cfg.get("company_name", "")).strip()
    if not company_name:
        return None

    company = company_by_name(company_name)
    return str(company.company_id) if company else None


def _processed_dir(inbox_path):
    processed = inbox_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    return processed


def _archive_file(csv_path, processed_dir):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    destination = processed_dir / f"{stamp}-{csv_path.name}"
    counter = 1
    while destination.exists():
        destination = processed_dir / f"{stamp}-{counter}-{csv_path.name}"
        counter += 1
    shutil.move(str(csv_path), str(destination))
    return destination


def sync_proofpix_inbox(*, inbox_path=None, company_id=None):
    inbox_path = Path(inbox_path).resolve() if inbox_path else resolve_inbox_path()
    if not inbox_path:
        raise ValueError("PROOFPIX_INBOX_PATH is not configured")

    if not inbox_path.is_dir():
        raise ValueError(f"Inbox folder does not exist: {inbox_path}")

    company_id = company_id or resolve_inbox_company_id()
    if not company_id:
        raise ValueError("PROOFPIX_INBOX_COMPANY is not configured or company was not found")

    company = company_by_id(company_id)
    if not company:
        raise ValueError("Configured inbox company was not found")

    csv_files = sorted(
        path
        for path in inbox_path.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv"
    )

    if not csv_files:
        return {
            "company": company.name,
            "inbox": str(inbox_path),
            "files_processed": 0,
            "files": [],
            "imported": 0,
            "updated": 0,
            "tasks_created": 0,
            "unmatched": [],
            "total_rows": 0,
        }

    processed_dir = _processed_dir(inbox_path)
    summary = {
        "company": company.name,
        "inbox": str(inbox_path),
        "files_processed": 0,
        "files": [],
        "imported": 0,
        "updated": 0,
        "tasks_created": 0,
        "unmatched": [],
        "total_rows": 0,
    }

    for csv_path in csv_files:
        file_result = {
            "filename": csv_path.name,
            "imported": 0,
            "updated": 0,
            "tasks_created": 0,
            "total_rows": 0,
            "unmatched": [],
            "error": None,
            "archived_to": None,
        }

        try:
            rows = parse_proofpix_csv(csv_path)
            results = import_proofpix_orders(company_id, rows, create_tasks=True)
            file_result.update(
                {
                    "imported": results["imported"],
                    "updated": results["updated"],
                    "tasks_created": results["tasks_created"],
                    "total_rows": results["total_rows"],
                    "unmatched": results["unmatched"],
                }
            )
            archived = _archive_file(csv_path, processed_dir)
            file_result["archived_to"] = str(archived)
            summary["files_processed"] += 1
        except Exception as exc:
            file_result["error"] = str(exc)

        summary["files"].append(file_result)
        summary["imported"] += file_result["imported"]
        summary["updated"] += file_result["updated"]
        summary["tasks_created"] += file_result["tasks_created"]
        summary["total_rows"] += file_result["total_rows"]
        summary["unmatched"].extend(file_result["unmatched"])

    return summary
