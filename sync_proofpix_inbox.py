#!/usr/bin/env python3
"""Import Proof Pix CSV files from the configured inbox folder."""

import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    from app import app, db
    from util.order_line_schema import ensure_order_lines_table
    from util.proofpix_inbox_sync import sync_proofpix_inbox

    with app.app_context():
        ensure_order_lines_table()
        try:
            results = sync_proofpix_inbox()
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        except Exception as exc:
            print(json.dumps({"error": f"Inbox sync failed: {exc}"}), file=sys.stderr)
            db.session.rollback()
            return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
