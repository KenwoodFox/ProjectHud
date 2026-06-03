import threading

from app.services.inventree_service import InvenTreeService


def get_inventree_service(screen_id: int, config: dict) -> InvenTreeService:
    from flask import current_app

    services = current_app.extensions.setdefault("inventree_services", {})
    if screen_id not in services:
        service = InvenTreeService(
            base_url=config["base_url"],
            username=config["username"],
            password=config["password"],
        )
        services[screen_id] = service
        try:
            service.bootstrap()
        except Exception as exc:
            print(f"InvenTree bootstrap failed: {exc}")
        threading.Thread(target=service.fetch_data, daemon=True).start()
    return services[screen_id]
