#!/usr/bin/env python3
"""Remove legacy calendar imports (Numbers, manual) and linked school tasks."""

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--company",
        default="White Raven",
        help="Company name to clean up (default: White Raven)",
    )
    args = parser.parse_args()

    from app import app, db
    from util.calendar_cleanup import clear_legacy_calendar_data

    with app.app_context():
        try:
            results = clear_legacy_calendar_data(company_name=args.company)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        except Exception as exc:
            print(json.dumps({"error": f"Calendar cleanup failed: {exc}"}), file=sys.stderr)
            db.session.rollback()
            return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
