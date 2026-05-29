#!/bin/sh
set -e

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

if [ ! -f ./populated ]; then
  python3 populate_db.py
  touch ./populated
fi

exec gunicorn --config gunicorn_config.py "app:app"
