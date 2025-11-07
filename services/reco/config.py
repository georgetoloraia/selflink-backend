from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    default_limit: int = Field(200, alias="RECO_DEFAULT_LIMIT")
    max_follow_sources: int = Field(200, alias="RECO_MAX_FOLLOWS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
