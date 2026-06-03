import json
import os
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app import store
from app.screen_types import SCREEN_TYPES, screen_summary, screen_type_choices, validate_config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

_SENSITIVE_FIELDS = {"token", "password"}


def admin_password_configured() -> bool:
    return bool(os.getenv("ADMIN_PASSWORD"))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped


def _config_for_display(screen_type: str, config: dict) -> dict:
    displayed = dict(config)
    for field in SCREEN_TYPES.get(screen_type, {}).get("fields", []):
        if field["name"] in _SENSITIVE_FIELDS and displayed.get(field["name"]):
            displayed[field["name"]] = "••••••••"
    return displayed


def _screens_for_template():
    rows = []
    for screen in store.list_screens():
        rows.append(
            {
                **screen,
                "type_label": SCREEN_TYPES[screen["screen_type"]]["label"],
                "summary": screen_summary(screen["screen_type"], screen["config"]),
                "config_display": _config_for_display(
                    screen["screen_type"], screen["config"]
                ),
            }
        )
    return rows


def _config_from_form(screen_type: str) -> dict:
    spec = SCREEN_TYPES[screen_type]
    config = {}
    for field in spec["fields"]:
        config[field["name"]] = request.form.get(field["name"], "")
    return config


def _invalidate_screen_service(screen_id: int):
    for ext_key in ("github_services", "gitea_services", "inventree_services"):
        services = current_app.extensions.get(ext_key)
        if services and screen_id in services:
            del services[screen_id]


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if not admin_password_configured():
        return render_template("admin/login.html", configured=False), 503

    if request.method == "POST":
        if request.form.get("password") == os.getenv("ADMIN_PASSWORD"):
            session["admin"] = True
            return redirect(url_for("admin.index"))
        flash("Invalid password.", "error")

    return render_template("admin/login.html", configured=True)


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@admin_required
def index():
    return render_template(
        "admin/index.html",
        settings=store.list_settings(),
        screens=_screens_for_template(),
        screen_types=SCREEN_TYPES,
        screen_types_json=json.dumps(SCREEN_TYPES),
        screen_type_choices=screen_type_choices(),
    )


@admin_bp.route("/settings", methods=["POST"])
@admin_required
def save_setting():
    try:
        store.set_setting(request.form["key"], request.form.get("value", ""))
        flash("Setting saved.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.index"))


@admin_bp.route("/settings/<key>/edit", methods=["GET", "POST"])
@admin_required
def edit_setting(key: str):
    setting = store.get_setting_row(key)
    if not setting:
        abort(404)

    if request.method == "POST":
        try:
            store.update_setting(
                request.form["old_key"],
                request.form["key"],
                request.form.get("value", ""),
            )
            flash("Setting updated.", "success")
            return redirect(url_for("admin.index"))
        except ValueError as exc:
            flash(str(exc), "error")

    return render_template("admin/edit_setting.html", setting=setting)


@admin_bp.route("/settings/delete", methods=["POST"])
@admin_required
def delete_setting():
    store.delete_setting(request.form["key"])
    flash("Setting removed.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/screens", methods=["POST"])
@admin_required
def add_screen():
    screen_type = request.form.get("screen_type", "").strip()
    if screen_type not in SCREEN_TYPES:
        flash("Choose a screen type.", "error")
        return redirect(url_for("admin.index"))

    try:
        config = validate_config(screen_type, _config_from_form(screen_type))
        store.add_screen(screen_type, config)
        flash(f"Added {SCREEN_TYPES[screen_type]['label']}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.index"))


@admin_bp.route("/screens/<int:screen_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_screen(screen_id: int):
    screen = store.get_screen(screen_id)
    if not screen:
        abort(404)

    screen_type = screen["screen_type"]
    if screen_type not in SCREEN_TYPES:
        abort(404)

    if request.method == "POST":
        try:
            store.update_screen(screen_id, _config_from_form(screen_type))
            _invalidate_screen_service(screen_id)
            flash("Screen updated.", "success")
            return redirect(url_for("admin.index"))
        except ValueError as exc:
            flash(str(exc), "error")

    return render_template(
        "admin/edit_screen.html",
        screen=screen,
        type_label=SCREEN_TYPES[screen_type]["label"],
        screen_types_json=json.dumps(SCREEN_TYPES),
        config_json=json.dumps(screen["config"]),
    )


@admin_bp.route("/screens/delete", methods=["POST"])
@admin_required
def delete_screen():
    screen_id = int(request.form["id"])
    store.delete_screen(screen_id)
    _invalidate_screen_service(screen_id)
    flash("Screen removed.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/screens/move", methods=["POST"])
@admin_required
def move_screen():
    store.move_screen(int(request.form["id"]), request.form["direction"])
    return redirect(url_for("admin.index"))
