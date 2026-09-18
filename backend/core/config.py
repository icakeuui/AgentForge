import os
from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import yaml
from dotenv import dotenv_values

# Determine project root based on backend module location
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # Mandatory fields
    MODEL_API_KEY: str = ""
    MODEL_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    DB_URL: str
    REDIS_URL: str
    JWT_SECRET: str = "agentforge-secret-key-phase-7"
    AGENT_CONFIG_SECRET: str = "agentforge-agent-config-secret"
    ACCESS_TOKEN_TTL_SECONDS: int = 3600
    REFRESH_TOKEN_TTL_SECONDS: int = 60 * 60 * 24 * 30
    AUTH_DEV_BYPASS_ENABLED: bool = False
    AUTH_DEV_USER_ID: str = "dev-user"
    AUTH_DEV_TEAM_ID: str = "00000000-0000-0000-0000-000000000001"
    AUTH_DEV_ROLE: str = "developer"
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 587
    # SMTP credentials must come from the environment (QQ authorization code,
    # never the account password). The host/transport defaults match QQ's
    # submission endpoint; deployments can override them through .env.
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "AgentForge"
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 5
    EMAIL_DELIVERY_MODE: str = "smtp"
    AVATAR_STORAGE_PROVIDER: str = "local"
    AVATAR_PUBLIC_BASE_URL: str = ""
    OBJECT_STORAGE_ENDPOINT: str = ""
    OBJECT_STORAGE_REGION: str = ""
    OBJECT_STORAGE_BUCKET: str = ""
    OBJECT_STORAGE_ACCESS_KEY: str = ""
    OBJECT_STORAGE_SECRET_KEY: str = ""
    OBJECT_STORAGE_PUBLIC_BASE_URL: str = ""
    OBJECT_STORAGE_USE_SSL: bool = True
    OBJECT_STORAGE_VERIFY_TLS: bool = True
    OBJECT_STORAGE_FORCE_PATH_STYLE: bool = True
    OBJECT_STORAGE_PUBLIC_READ: bool = True
    EMAIL_VERIFICATION_CODE_TTL_SECONDS: int = 600
    PASSWORD_RESET_CODE_TTL_SECONDS: int = 600
    EMAIL_SEND_RATE_LIMIT_SECONDS: int = 60
    EMAIL_SEND_MAX_RETRIES: int = 3
    EMAIL_SEND_RETRY_DELAYS_SECONDS: str = "1,3"
    REGISTRATION_TOKEN_TTL_SECONDS: int = 1800
    SEARCH_ID_MIN: int = 10000000
    SEARCH_ID_MAX: int = 99999999
    DEFAULT_TEAM_TOKEN_LIMIT: int = 1000000
    DEFAULT_TEAM_RATE_LIMIT: int = 100
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "agentforge_knowledge"
    
    # Optional fields with defaults
    ENV: str = "dev"
    APP_NAME: str = "AgentForge"
    LOG_LEVEL: str = "INFO"
    CORS_ALLOWED_ORIGINS: Any = [
        "http://localhost:3000",
        "http://localhost:4174",
        "http://localhost:4175",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4174",
        "http://127.0.0.1:4175",
        "http://127.0.0.1:5173",
        "http://localhost:5276",
        "http://127.0.0.1:5276",
    ]
    
    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    # Stable configuration for .env location
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @classmethod
    def load_config(cls):
        # 1. Load YAML (lowest priority)
        yaml_config_path = PROJECT_ROOT / os.getenv("CONFIG_PATH", "backend/config.yaml")
        yaml_data = {}
        if yaml_config_path.exists():
            with open(yaml_config_path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
        
        # 2. Get high-priority values from .env and environment variables
        # Priority order: os.environ > .env
        dotenv_path = str(PROJECT_ROOT / ".env")
        env_vars = {**dotenv_values(dotenv_path), **os.environ}
        
        # 3. Filter YAML: only use YAML if the field is not present in Env or Dotenv.
        # This achieves: Env > Dotenv > YAML > Defaults
        yaml_data = {
            k: v for k, v in yaml_data.items() 
            if k not in env_vars or not env_vars[k]
        }

        yaml_env = str(yaml_data.get("ENV") or env_vars.get("ENV") or "dev").lower()
        yaml_db_url = str(yaml_data.get("DB_URL") or "")
        is_placeholder_db = yaml_db_url.startswith("postgresql+asyncpg://user:password@localhost")
        if yaml_env in {"dev", "development", "local"} and is_placeholder_db:
            yaml_data["DB_URL"] = f"sqlite+aiosqlite:///{PROJECT_ROOT / 'agentforge_preview.db'}"
        elif yaml_db_url.startswith("sqlite+aiosqlite:///./"):
            yaml_data["DB_URL"] = f"sqlite+aiosqlite:///{PROJECT_ROOT / yaml_db_url.removeprefix('sqlite+aiosqlite:///./')}"
        
        # 4. Initialize Settings.
        settings = cls(**yaml_data)

        return settings

    @property
    def is_dev_env(self) -> bool:
        return self.ENV.lower() in {"dev", "development", "local"}

    @property
    def auth_dev_bypass_enabled(self) -> bool:
        return self.AUTH_DEV_BYPASS_ENABLED

    @property
    def is_prod_like_env(self) -> bool:
        return self.ENV.lower() in {"prod", "production", "staging"}

    @property
    def effective_model_api_key(self) -> str:
        if self.OPENROUTER_API_KEY:
            return self.OPENROUTER_API_KEY
        return self.MODEL_API_KEY

    @property
    def effective_model_base_url(self) -> str:
        if self.OPENROUTER_BASE_URL:
            return self.OPENROUTER_BASE_URL
        return self.MODEL_BASE_URL

    @property
    def effective_default_model(self) -> str:
        if self.OPENROUTER_MODEL:
            return self.OPENROUTER_MODEL
        return "openai/gpt-4o-mini"

settings = Settings.load_config()
