import os

from sqlalchemy import func

from app.extensions import db
from app.models import Screen, Setting
from app.screen_types import SCREEN_TYPES, validate_config
from config import database_path


def _ensure_database_writable():
    path = database_path()
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)
    if not os.access(directory, os.W_OK):
        raise RuntimeError(
            f"Database directory is not writable: {directory}\n"
            f"Fix with: chmod u+w {directory}"
        )
    if path.exists() and not os.access(path, os.W_OK):
        raise RuntimeError(
            f"Database file is not writable: {path}\n"
            f"Fix with: chmod u+w {path}  (or remove it and restart)"
        )


def _purge_unknown_screens():
    """Drop screens whose type was removed from the app (no legacy handlers)."""
    stale = list(
        db.session.scalars(
            db.select(Screen).where(Screen.screen_type.notin_(SCREEN_TYPES))
        )
    )
    if not stale:
        return
    for row in stale:
        db.session.delete(row)
    db.session.commit()


def init_db():
    _ensure_database_writable()
    db.create_all()
    _purge_unknown_screens()
    if db.session.scalar(db.select(func.count()).select_from(Setting)) == 0:
        _seed()


def _seed():
    db.session.add(
        Setting(
            key="refresh_duration",
            value=os.getenv("REFRESH_DURATION", "25"),
        )
    )

    position = 0
    if os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_REPOS"):
        db.session.add(
            Screen(
                screen_type="github_table",
                config={
                    "token": os.getenv("GITHUB_TOKEN", ""),
                    "repos": os.getenv("GITHUB_REPOS", ""),
                    "username_map": os.getenv("USERNAME_MAP", ""),
                },
                position=position,
            )
        )
        position += 1

    for env_key in ("COUNT_DOWN", "COUNT_DOWN2"):
        value = os.getenv(env_key)
        if not value:
            continue
        timestamp, label = value.split(":", 1)
        db.session.add(
            Screen(
                screen_type="countdown",
                config={"timestamp": timestamp, "label": label},
                position=position,
            )
        )
        position += 1

    db.session.commit()


def list_settings() -> list[dict]:
    return [
        {"key": s.key, "value": s.value}
        for s in db.session.scalars(
            db.select(Setting).order_by(Setting.key)
        )
    ]


def get_setting(key: str, default: str | None = None) -> str | None:
    row = db.session.get(Setting, key)
    return row.value if row else default


def get_setting_row(key: str) -> dict | None:
    row = db.session.get(Setting, key)
    if not row:
        return None
    return {"key": row.key, "value": row.value}


def set_setting(key: str, value: str):
    key = key.strip()
    if not key:
        raise ValueError("Key is required")
    db.session.merge(Setting(key=key, value=value))
    db.session.commit()


def update_setting(old_key: str, new_key: str, value: str):
    old_key = old_key.strip()
    new_key = new_key.strip()
    if not new_key:
        raise ValueError("Key is required")
    row = db.session.get(Setting, old_key)
    if not row:
        raise ValueError("Setting not found")
    if old_key != new_key:
        if db.session.get(Setting, new_key):
            raise ValueError(f"Setting {new_key!r} already exists")
        db.session.delete(row)
        db.session.add(Setting(key=new_key, value=value))
    else:
        row.value = value
    db.session.commit()


def delete_setting(key: str):
    if row := db.session.get(Setting, key):
        db.session.delete(row)
        db.session.commit()


def list_screen_paths() -> list[str]:
    screens = db.session.scalars(
        db.select(Screen)
        .where(Screen.enabled.is_(True))
        .order_by(Screen.position, Screen.id)
    )
    return [s.display_path for s in screens]


def list_screens() -> list[dict]:
    screens = db.session.scalars(
        db.select(Screen).order_by(Screen.position, Screen.id)
    )
    return [s.to_dict() for s in screens]


def get_screen(screen_id: int) -> dict | None:
    row = db.session.get(Screen, screen_id)
    return row.to_dict() if row else None


def add_screen(screen_type: str, config: dict):
    if screen_type not in SCREEN_TYPES:
        raise ValueError(f"Unknown screen type: {screen_type}")
    max_pos = db.session.scalar(db.select(func.max(Screen.position))) or -1
    db.session.add(
        Screen(
            screen_type=screen_type,
            config=validate_config(screen_type, config),
            position=max_pos + 1,
        )
    )
    db.session.commit()


def update_screen(screen_id: int, config: dict):
    row = db.session.get(Screen, screen_id)
    if not row:
        raise ValueError("Screen not found")
    row.config = validate_config(
        row.screen_type, config, existing=row.config or {}
    )
    db.session.commit()


def delete_screen(screen_id: int):
    if row := db.session.get(Screen, screen_id):
        db.session.delete(row)
        db.session.commit()


def move_screen(screen_id: int, direction: str):
    screens = list(
        db.session.scalars(db.select(Screen).order_by(Screen.position, Screen.id))
    )
    ids = [s.id for s in screens]
    if screen_id not in ids:
        return
    idx = ids.index(screen_id)
    if direction == "up" and idx > 0:
        partner = screens[idx - 1]
    elif direction == "down" and idx < len(screens) - 1:
        partner = screens[idx + 1]
    else:
        return
    current = screens[idx]
    current.position, partner.position = partner.position, current.position
    db.session.commit()
