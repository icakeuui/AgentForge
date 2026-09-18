from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MarketplaceSettings(BaseSettings):
    database_url: str | None = None
    manifest_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent / "manifests")
    mcp_stdio_timeout: float = 30.0
    mcp_http_timeout: float = 30.0
    mcp_health_check_interval: int = 60
    builtin_enabled: bool = True

    model_config = SettingsConfigDict(
        env_prefix="PLUGIN_MARKETPLACE_",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> MarketplaceSettings:
    return MarketplaceSettings()


# Singleton settings instance used throughout the module
settings = get_settings()
