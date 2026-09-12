from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OMNITRADE_", env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./omnitrade.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "development-only-secret-change-before-use"
    artifact_dir: Path = Path("artifacts")
    fixture_mode: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
