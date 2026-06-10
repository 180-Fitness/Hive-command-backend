#!/usr/bin/env python3
"""Seed or clear demo school-shoot data for the delivery report."""

import argparse
import json
import sys
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()


def _parse_month(value):
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Month must be YYYY-MM") from exc
    return parsed.date().replace(day=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--month",
        type=_parse_month,
        help="Test month to seed (YYYY-MM). Defaults to the previous calendar month.",
    )
    parser.add_argument(
        "--company",
        default="White Raven",
        help="Company name to seed (default: White Raven)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Remove demo delivery-report data without re-seeding",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Keep existing demo data and add another batch",
    )
    args = parser.parse_args()

    from app import app, db
    from util.delivery_report_demo_seed import (
        clear_delivery_report_demo,
        seed_delivery_report_demo,
    )

    with app.app_context():
        try:
            if args.clear:
                results = clear_delivery_report_demo(company_name=args.company)
            else:
                results = seed_delivery_report_demo(
                    month_start=args.month,
                    company_name=args.company,
                    replace=not args.no_replace,
                )
        except (ValueError, RuntimeError) as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        except Exception as exc:
            print(json.dumps({"error": f"Demo seed failed: {exc}"}), file=sys.stderr)
            db.session.rollback()
            return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
