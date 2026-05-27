from flask import Blueprint, render_template

from app import store

index_bp = Blueprint("main", __name__)


@index_bp.route("/")
def index():
    refresh = store.get_setting("refresh_duration", "25")
    try:
        refresh_duration = int(refresh)
    except (TypeError, ValueError):
        refresh_duration = 25
    return render_template("index.html", refresh_duration=refresh_duration)
