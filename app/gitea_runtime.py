import threading

from app.services.gitea_service import GiteaService


def _parse_username_map(value: str) -> dict:
    return {
        pair.split(":")[0]: pair.split(":")[1]
        for pair in (value or "").split(",")
        if ":" in pair
    }


def get_gitea_service(screen_id: int, config: dict) -> GiteaService:
    from flask import current_app

    services = current_app.extensions.setdefault("gitea_services", {})
    if screen_id not in services:
        repos = [r.strip() for r in config.get("repos", "").split(",") if r.strip()]
        service = GiteaService(
            base_url=config["base_url"],
            token=config["token"],
            organization=config["organization"],
            repos=repos,
            username_mapping=_parse_username_map(config.get("username_map", "")),
        )
        services[screen_id] = service
        threading.Thread(target=service.fetch_data, daemon=True).start()
    return services[screen_id]
