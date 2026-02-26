from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # AI (Anthropic Claude)
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-3-5-haiku-20241022"

    # App
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"] # Default Frontend URL


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
