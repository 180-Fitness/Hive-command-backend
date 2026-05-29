from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from lib.loaders import load_models

__all__ = ("db", "init_db", "query")

db = SQLAlchemy()
query = db.session.query


def init_db(app=None, db_instance=None):
    if isinstance(app, Flask) and isinstance(db_instance, SQLAlchemy):
        load_models()
        db_instance.init_app(app)
    else:
        raise ValueError("Cannot initialize database without Flask app and SQLAlchemy instance.")
