from pydantic_settings import BaseSettings
from functools import lru_cache
 
 
class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-20250514"
    log_level: str = "INFO"
    app_env: str = "development"
 
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
 
 
@lru_cache()
def get_settings() -> Settings:
    return Settings()