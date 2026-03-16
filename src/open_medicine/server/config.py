"""Service configuration via environment variables."""
from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OM_")

    host: str = "0.0.0.0"
    port: int = 8000
    auth_mode: Literal["none", "api_key"] = "none"
    api_keys: str = ""

    @property
    def valid_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}
