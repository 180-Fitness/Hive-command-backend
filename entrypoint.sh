#!/bin/sh
set -e

if [ ! -f ./populated ]; then
  python3 populate_db.py
  touch ./populated
fi

exec gunicorn --config gunicorn_config.py "app:app"
