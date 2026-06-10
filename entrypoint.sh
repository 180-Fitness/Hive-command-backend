#!/bin/sh
set -e

python3 -c "from app import app, db; from util.project_schema import ensure_project_columns; app.app_context().push(); db.create_all(); ensure_project_columns()"

if [ ! -f ./populated ]; then
  python3 populate_db.py
  touch ./populated
fi

exec gunicorn --config gunicorn_config.py "app:app"
