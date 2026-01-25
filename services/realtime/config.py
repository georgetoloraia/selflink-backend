from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SelfLink Realtime Gateway"
    log_level: str = "info"
    host: str = Field("0.0.0.0", alias="REALTIME_HOST")
    port: int = Field(8001, alias="REALTIME_PORT")
    redis_url: str = Field("redis://localhost:6379/1", alias="REALTIME_REDIS_URL")
    jwt_signing_key: str | None = Field(None, alias="JWT_SIGNING_KEY")
    realtime_jwt_secret: str | None = Field(None, alias="REALTIME_JWT_SECRET")
    realtime_publish_token: str | None = Field(None, alias="REALTIME_PUBLISH_TOKEN")
    realtime_publish_rate_limit: str | None = Field(None, alias="REALTIME_PUBLISH_RATE_LIMIT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    @property
    def jwt_secret(self) -> str:
        if self.realtime_jwt_secret and self.realtime_jwt_secret.strip():
            return self.realtime_jwt_secret
        if self.jwt_signing_key and self.jwt_signing_key.strip():
            return self.jwt_signing_key
        return "unsafe-realtime-secret"


settings = Settings()
