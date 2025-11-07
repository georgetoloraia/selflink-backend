from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SelfLink Realtime Gateway"
    log_level: str = "info"
    host: str = Field("0.0.0.0", alias="REALTIME_HOST")
    port: int = Field(8001, alias="REALTIME_PORT")
    redis_url: str = Field("redis://localhost:6379/1", alias="REALTIME_REDIS_URL")
    jwt_secret: str = Field("unsafe-realtime-secret", alias="REALTIME_JWT_SECRET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
