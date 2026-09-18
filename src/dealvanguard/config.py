from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)


class Settings(BaseSettings):
    """
    Application environment settings.
    Reads variables from .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    anthropic_api_key: Optional[str] = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
        description="Anthropic secret key."
    )
    model_name: str = Field(
        default="claude-3-7-sonnet-20250219",
        validation_alias="MODEL_NAME",
        description="Default Claude model name."
    )
    log_level: str = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
        description="Logging level threshold."
    )


settings = Settings()