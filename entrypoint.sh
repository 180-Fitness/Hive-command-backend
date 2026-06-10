#!/bin/sh
set -e

python3 -c "from app import app, db; app.app_context().push(); db.create_all()"

if [ ! -f ./populated ]; then
  python3 populate_db.py
  touch ./populated
fi

exec gunicorn --config gunicorn_config.py "app:app"
