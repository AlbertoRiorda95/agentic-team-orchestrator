"""Configuration, read from environment variables only."""

from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # Required to serve requests; no default, so no credentials live in the code.
    # Read at startup (not at import), so the contract can be exported without it.
    database_url: SecretStr | None = None
    # Comma separated in the environment: CORS_ORIGINS=http://a,http://b
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:8081"]
    git_sha: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", "git_sha", mode="before")
    @classmethod
    def blank_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value
