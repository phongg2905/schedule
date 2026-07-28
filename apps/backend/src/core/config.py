from functools import lru_cache
from pathlib import Path


from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(Path(__file__).resolve().parents[4] / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = ""
    direct_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_refresh_secret: str = "change-me-refresh"
    openai_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    staging_strategy: str = "synthetic"

    @field_validator("staging_strategy")
    @classmethod
    def _validate_staging_strategy(cls, v: str) -> str:
        allowed = {"synthetic", "retrained"}
        normalized = v.lower()
        if normalized not in allowed:
            raise ValueError(
                f"Invalid STAGING_STRATEGY: {v!r}. Must be one of: {', '.join(sorted(allowed))}"
            )
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
