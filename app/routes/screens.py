import os

from flask import Blueprint, abort, jsonify, render_template

from app import store
from app.gitea_runtime import get_gitea_service
from app.github_runtime import get_github_service

screens_bp = Blueprint("screens", __name__)


@screens_bp.route("/api/screens")
def get_screens():
    screens = store.list_screen_paths()
    return jsonify({"version": os.getenv("GIT_COMMIT", None), "screens": screens})


@screens_bp.route("/screen/<int:screen_id>")
def show_screen(screen_id: int):
    screen = store.get_screen(screen_id)
    if not screen or not screen["enabled"]:
        abort(404)

    screen_type = screen["screen_type"]
    config = screen["config"]

    if screen_type == "generic":
        return render_template("screen/generic.html", url=config["url"])

    if screen_type == "countdown":
        try:
            target_time = int(config["timestamp"])
        except (KeyError, ValueError):
            target_time = 0
        return render_template(
            "countdown.html",
            target_time=target_time,
            event_name=config.get("label", "Event"),
        )

    if screen_type == "github_table":
        service = get_github_service(screen_id, config)
        return render_template(
            "table.html",
            **service.latest_data,
            last_updated=service.last_updated,
        )

    if screen_type == "github_pending":
        service = get_github_service(screen_id, config)
        return render_template(
            "pending.html",
            **service.latest_data,
            last_updated=service.last_updated,
        )

    if screen_type == "gitea_table":
        service = get_gitea_service(screen_id, config)
        return render_template(
            "table.html",
            **service.latest_data,
            last_updated=service.last_updated,
        )

    if screen_type == "gitea_pending":
        service = get_gitea_service(screen_id, config)
        return render_template(
            "pending.html",
            **service.latest_data,
            last_updated=service.last_updated,
        )

    if screen_type == "gitea_projects":
        service = get_gitea_service(screen_id, config)
        return render_template(
            "screen/projects.html",
            projects=service.latest_data.get("projects", []),
            last_updated=service.last_updated,
        )

    abort(404)


@screens_bp.route("/test")
def test_screen():
    return f"""
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: #222;
                color: white;
                font-family: "Courier New", Courier, monospace;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h1>ProjectHUD Starting! Version {os.getenv('GIT_COMMIT', 'Unknown')}</h1>
    </body>
    </html>
    """
