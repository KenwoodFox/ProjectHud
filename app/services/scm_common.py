from datetime import datetime


def empty_table_data() -> dict:
    return {
        "milestones": [],
        "issues": [],
        "pull_requests": [],
        "issues_count": 0,
        "pull_requests_count": 0,
        "pending_reviews": [],
        "commits": [],
        "ci_jobs": [],
        "projects": [],
    }


def to_local_naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return to_local_naive(dt)


def label_color(color: str) -> str:
    if not color:
        return "#888"
    return color if color.startswith("#") else f"#{color}"


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def normalize_ci_run(
    *,
    repo_name: str,
    name: str,
    status: str | None,
    conclusion: str | None,
    started_at: datetime | None,
    ended_at: datetime | None,
) -> dict | None:
    if not started_at:
        return None

    status_l = (status or "").lower()
    conclusion_l = (conclusion or "").lower()
    running = ("queued", "waiting", "running", "in_progress", "pending")

    duration_seconds = None
    if status_l in running:
        duration_seconds = max(
            0, int((datetime.now() - started_at).total_seconds())
        )
    elif ended_at:
        duration_seconds = max(0, int((ended_at - started_at).total_seconds()))

    if status_l in running:
        passed = None
        display_status = "running"
    elif conclusion_l == "success" or status_l == "success":
        passed = True
        display_status = "passed"
    elif conclusion_l in (
        "failure",
        "failed",
        "cancelled",
        "timed_out",
        "skipped",
    ) or status_l in ("failure", "failed", "cancelled"):
        passed = False
        display_status = "failed"
    else:
        passed = None
        display_status = status_l or "unknown"

    return {
        "repo_name": repo_name,
        "name": name,
        "status": display_status,
        "passed": passed,
        "duration": format_duration(duration_seconds),
        "started_at": started_at,
    }
