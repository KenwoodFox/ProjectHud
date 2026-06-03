"""Built-in screen types and their admin form fields."""

SCREEN_TYPES = {
    "generic": {
        "label": "Generic URL",
        "description": "Embed any web page in the rotation.",
        "fields": [
            {
                "name": "url",
                "label": "URL",
                "type": "url",
                "placeholder": "https://example.com/dashboard",
                "required": True,
            },
        ],
    },
    "countdown": {
        "label": "Countdown",
        "description": "Count down to an event.",
        "fields": [
            {
                "name": "timestamp",
                "label": "Unix timestamp",
                "type": "number",
                "placeholder": "1773435600",
                "required": True,
            },
            {
                "name": "label",
                "label": "Event name",
                "type": "text",
                "placeholder": "Week 2 Competition",
                "required": True,
            },
        ],
    },
    "github_table": {
        "label": "GitHub — project table",
        "description": "Milestones, issues, and pull requests.",
        "fields": [
            {
                "name": "token",
                "label": "GitHub token",
                "type": "password",
                "required": True,
            },
            {
                "name": "repos",
                "label": "Repositories",
                "type": "text",
                "placeholder": "org/repo-one, org/repo-two",
                "required": True,
            },
            {
                "name": "username_map",
                "label": "Display names (optional)",
                "type": "text",
                "placeholder": "github-user:Display Name",
                "required": False,
            },
        ],
    },
    "github_pending": {
        "label": "GitHub — pending reviews",
        "description": "Who still needs to review open PRs.",
        "fields": [
            {
                "name": "token",
                "label": "GitHub token",
                "type": "password",
                "required": True,
            },
            {
                "name": "repos",
                "label": "Repositories",
                "type": "text",
                "placeholder": "org/repo-one, org/repo-two",
                "required": True,
            },
            {
                "name": "username_map",
                "label": "Display names (optional)",
                "type": "text",
                "placeholder": "github-user:Display Name",
                "required": False,
            },
        ],
    },
    "gitea_table": {
        "label": "Gitea — project table",
        "description": "Open issues and PRs for a Gitea organization (with commit log).",
        "fields": [
            {
                "name": "base_url",
                "label": "Gitea URL",
                "type": "url",
                "placeholder": "https://gitea.example.com",
                "required": True,
            },
            {
                "name": "token",
                "label": "Gitea token",
                "type": "password",
                "required": True,
            },
            {
                "name": "organization",
                "label": "Organization",
                "type": "text",
                "placeholder": "my-org",
                "required": True,
            },
            {
                "name": "repos",
                "label": "Repositories (optional)",
                "type": "text",
                "placeholder": "org/repo-one — leave blank for all org repos",
                "required": False,
            },
            {
                "name": "username_map",
                "label": "Display names (optional)",
                "type": "text",
                "placeholder": "gitea-user:Display Name",
                "required": False,
            },
        ],
    },
    "inventree_dashboard": {
        "label": "InvenTree — inventory dashboard",
        "description": "Recent parts, outstanding orders, and production builds.",
        "fields": [
            {
                "name": "base_url",
                "label": "InvenTree URL",
                "type": "url",
                "placeholder": "https://inventree.example.com",
                "required": True,
            },
            {
                "name": "username",
                "label": "Username",
                "type": "text",
                "required": True,
            },
            {
                "name": "password",
                "label": "Password",
                "type": "password",
                "required": True,
            },
        ],
    },
    "gitea_pending": {
        "label": "Gitea — pending reviews",
        "description": "Who still needs to review open PRs on Gitea.",
        "fields": [
            {
                "name": "base_url",
                "label": "Gitea URL",
                "type": "url",
                "placeholder": "https://gitea.example.com",
                "required": True,
            },
            {
                "name": "token",
                "label": "Gitea token",
                "type": "password",
                "required": True,
            },
            {
                "name": "organization",
                "label": "Organization",
                "type": "text",
                "placeholder": "my-org",
                "required": True,
            },
            {
                "name": "repos",
                "label": "Repositories (optional)",
                "type": "text",
                "placeholder": "org/repo-one — leave blank for all org repos",
                "required": False,
            },
            {
                "name": "username_map",
                "label": "Display names (optional)",
                "type": "text",
                "placeholder": "gitea-user:Display Name",
                "required": False,
            },
        ],
    },
}


def screen_type_choices():
    return [(key, spec["label"]) for key, spec in SCREEN_TYPES.items()]


_SENSITIVE_FIELD_NAMES = {"token", "password"}


def validate_config(
    screen_type: str, config: dict, existing: dict | None = None
) -> dict:
    if screen_type not in SCREEN_TYPES:
        raise ValueError(f"Unknown screen type: {screen_type}")

    existing = existing or {}
    spec = SCREEN_TYPES[screen_type]
    cleaned = {}
    for field in spec["fields"]:
        name = field["name"]
        value = (config.get(name) or "").strip()
        if not value and name in _SENSITIVE_FIELD_NAMES and existing.get(name):
            cleaned[name] = existing[name]
            continue
        if field.get("required") and not value:
            raise ValueError(f"{field['label']} is required")
        if value:
            cleaned[name] = value

    if screen_type in ("gitea_table", "gitea_pending", "inventree_dashboard") and cleaned.get(
        "base_url"
    ):
        from app.services.inventree_service import normalize_inventree_base_url

        url = cleaned["base_url"]
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        cleaned["base_url"] = normalize_inventree_base_url(url)

    if screen_type == "generic" and cleaned.get("url"):
        url = cleaned["url"]
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

    if screen_type == "countdown" and "timestamp" in cleaned:
        try:
            int(cleaned["timestamp"])
        except ValueError as exc:
            raise ValueError("Unix timestamp must be a number") from exc

    return cleaned


def screen_summary(screen_type: str, config: dict) -> str:
    if screen_type == "generic":
        return config.get("url", "")
    if screen_type == "countdown":
        return f"{config.get('label', 'Event')} ({config.get('timestamp', '?')})"
    if screen_type in ("github_table", "github_pending"):
        repos = config.get("repos", "")
        return repos or "GitHub"
    if screen_type in ("gitea_table", "gitea_pending"):
        org = config.get("organization", "")
        repos = config.get("repos", "")
        return repos or org or "Gitea"
    if screen_type == "inventree_dashboard":
        user = config.get("username", "")
        host = config.get("base_url", "")
        return f"{user} @ {host}" if user and host else "InvenTree"
    return screen_type
