#!/bin/sh
export FLASK_APP=app.py
flask db migrate -m "$1"
flask db upgrade
