"""Central configuration for FindBack.

Every configuration value comes from environment variables. A local `.env`
file (never committed) is loaded automatically with a tiny built-in parser so
no extra dependency is required.
"""

from __future__ import annotations

import os
from pathlib import Path

# backend/ directory (one level above app/)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path) -> None:
    """Minimal .env parser: KEY=VALUE lines, `#` comments, optional quotes.

    Values already present in the real environment always win, so the process
    environment can override the file.
    """
    if not path.exists():
        return
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file(ENV_FILE)


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(
            f"Missing required environment variable '{name}'. "
            f"Set it in the process environment or in {ENV_FILE} "
            f"(copy .env.example to .env first)."
        )
    return value


class Settings:
    """Application settings - single source of truth (see MASTER_README §79)."""

    APP_NAME: str = "FindBack"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = _get("DEBUG", "true").lower() in {"1", "true", "yes"}

    # Database
    DATABASE_URL: str = _require("DATABASE_URL")

    # JWT
    SECRET_KEY: str = _require("SECRET_KEY")
    ALGORITHM: str = _get("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(_get("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # CORS
    FRONTEND_URL: str = _get("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in _get(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        ).split(",")
        if origin.strip()
    ]

    # AI (all optional - application must keep working without them)
    GEMINI_API_KEY: str = _get("GEMINI_API_KEY", "")
    EMBEDDING_MODEL: str = _get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    MATCH_TOP_K: int = int(_get("MATCH_TOP_K", "10"))

    # Matching weights (MASTER_README §31)
    W_TEXT: float = float(_get("W_TEXT", "0.50"))
    W_IMAGE: float = float(_get("W_IMAGE", "0.30"))
    W_LOCATION: float = float(_get("W_LOCATION", "0.15"))
    W_CATEGORY: float = float(_get("W_CATEGORY", "0.05"))

    # Uploads
    MEDIA_DIR: Path = Path(_get("MEDIA_DIR", str(BASE_DIR / "media")))
    MAX_UPLOAD_SIZE_MB: int = int(_get("MAX_UPLOAD_SIZE_MB", "5"))
    MAX_UPLOAD_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Pagination
    DEFAULT_PAGE_LIMIT: int = 20
    MAX_PAGE_LIMIT: int = 100


settings = Settings()
