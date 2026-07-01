from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./ai_planner_v2.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_refresh_secret: str = "change-me-refresh"
    openai_api_key: str = ""
    frontend_origin: str = "http://localhost:3000"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    debug_mode: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
