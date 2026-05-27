import os
from pathlib import Path

from sqlalchemy.pool import NullPool


def database_path() -> Path:
    raw = os.getenv("DATABASE_PATH", "data/projecthud.db")
    return Path(raw).expanduser().resolve()


def database_uri() -> str:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool,
        "connect_args": {"timeout": 30},
    }


class DevelopmentConfig(Config):
    pass


class ProductionConfig(Config):
    pass


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    return DevelopmentConfig
