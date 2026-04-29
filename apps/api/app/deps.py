"""Settings + dependencies."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Ładujemy oba: root workspace .env (źródło tokenów Meta+GHL) i lokalne dashboard .env (override).
    # Pydantic-settings: późniejszy plik nadpisuje wcześniejszy.
    model_config = SettingsConfigDict(
        env_file=(
            "/Users/dawiddziadkowiec/Salespros OS/.env",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Meta
    META_ACCESS_TOKEN: str
    META_AD_ACCOUNT_ID: str
    META_APP_ID: str | None = None

    # GHL
    GHL_PRIVATE_TOKEN: str
    GHL_LOCATION_ID: str
    GHL_API_VERSION: str = "2021-07-28"

    # Server
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000"
    REQUIRE_CF_ACCESS: bool = False
    CF_ACCESS_TEAM_DOMAIN: str | None = None
    CF_ACCESS_AUDIENCE: str | None = None

    # X-API-Key shared secret (alternatywa do Cloudflare Access)
    DASHBOARD_API_KEY: str | None = None
    REQUIRE_API_KEY: bool = False

    # Snapshots fallback
    SNAPSHOTS_DIR: str = ""

    # Cache + tz
    CACHE_TTL_SECONDS: int = 60
    DEFAULT_TZ: str = "Europe/Warsaw"

    # Campaign classification (CPL split: acquisition vs retarget)
    # VPS: /var/lib/salespros-dashboard/campaign_classification.json (mount volume)
    # Lokal: względem cwd
    CLASSIFICATION_FILE_PATH: str = "data/campaign_classification.json"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @property
    def snapshots_path(self) -> Path | None:
        if not self.SNAPSHOTS_DIR:
            return None
        p = Path(self.SNAPSHOTS_DIR)
        return p if p.exists() else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
