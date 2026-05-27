import os

from flask import Flask

from app.extensions import db
from app.filters.time_formatter import time_ago
from app.routes.admin import admin_bp
from app.routes.index import index_bp
from app.routes.screens import screens_bp


def create_app():
    from config import database_uri, get_config

    from app import models, store  # noqa: F401

    app = Flask(__name__)
    app.jinja_env.filters["time_ago"] = time_ago

    app.config.from_object(get_config())
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri()
    app.secret_key = os.getenv("SECRET_KEY", app.config["SECRET_KEY"])

    db.init_app(app)
    with app.app_context():
        store.init_db()

    app.register_blueprint(index_bp)
    app.register_blueprint(screens_bp)
    app.register_blueprint(admin_bp)

    return app
