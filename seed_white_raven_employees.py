#!/usr/bin/env python3
"""Create or sync White Raven employees from util.white_raven_employees."""

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
        help="Company name to seed employees for (default: White Raven)",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset existing users to the roster default password (Test123!)",
    )
    args = parser.parse_args()

    from app import app, db
    from util.white_raven_employee_seed import seed_white_raven_employees

    with app.app_context():
        try:
            results = seed_white_raven_employees(
                company_name=args.company,
                reset_password=args.reset_password,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}), file=sys.stderr)
            return 1
        except Exception as exc:
            print(json.dumps({"error": f"Employee seed failed: {exc}"}), file=sys.stderr)
            db.session.rollback()
            return 1

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
