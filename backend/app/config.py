import os
from typing import List
from urllib.parse import quote


def _env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return default if v is None or v == "" else v


def _database_url() -> str:
    """DATABASE_URL (SQLAlchemy URL) wins; otherwise DB_URL (plain or jdbc: style) + DB_USER/DB_PASSWORD."""
    direct = os.getenv("DATABASE_URL")
    if direct:
        return direct
    url = _env("DB_URL", "postgresql://localhost:5432/inkgrade")
    if url.startswith("jdbc:"):
        url = url[len("jdbc:"):]
    if url.startswith("sqlite"):
        return url
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    if "@" not in url.split("://", 1)[1]:
        user = quote(_env("DB_USER", "inkgrade"), safe="")
        password = quote(_env("DB_PASSWORD", "inkgrade"), safe="")
        scheme, rest = url.split("://", 1)
        url = f"{scheme}://{user}:{password}@{rest}"
    return url


class Settings:
    def __init__(self) -> None:
        self.database_url = _database_url()
        self.jwt_secret = _env("JWT_SECRET", "dev-only-secret-change-me-dev-only-secret-change-me")
        self.jwt_expiration_minutes = int(_env("JWT_EXPIRATION_MINUTES", "480"))
        self.cors_origins: List[str] = [o.strip() for o in _env(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]
        self.storage_root = _env("STORAGE_ROOT", "./uploads")
        self.ai_base_url = _env("AI_SERVICE_URL", "http://localhost:8001")
        self.ai_api_key = _env("AI_API_KEY", "")
        self.ai_timeout_seconds = int(_env("AI_TIMEOUT_SECONDS", "300"))
        self.admin_username = _env("ADMIN_USERNAME", "admin")
        self.admin_password = _env("ADMIN_PASSWORD", "Admin@123")
        self.admin_email = _env("ADMIN_EMAIL", "admin@inkgrade.local")
        self.seed_demo = _env("SEED_DEMO", "false").lower() == "true"
        self.max_upload_bytes = 25 * 1024 * 1024


settings = Settings()
