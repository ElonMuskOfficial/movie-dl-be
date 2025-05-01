from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    base_url: str = "http://127.0.0.1:8000"
    api_version: str = "v1"
    vegamovies_base_url: str = "https://vegamovies.bot"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()