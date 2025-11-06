from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 9010
    api_prefix: str = "/v1"

    elasticsearch_host: str = "localhost"
    elasticsearch_port: int = 9200
    elasticsearch_user: str = "admin"
    elasticsearch_password: str = "admin"
    elasticsearch_index: str = "company-data"

    cors_origins: list[str] | None = ["*"]
    cors_headers: list[str] = ["*"]

    breaker_failure_rate_threshold: float = 0.5
    breaker_minimum_calls: int = 8
    breaker_wait_duration_seconds: float = 30.0
    breaker_timeout_seconds: float = 5.0
    breaker_retry_attempts: int = 2
    breaker_retry_backoff_ms: int = 200
    breaker_retry_backoff_multiplier: float = 2.0

    class Config:
        env_prefix = "SEARCH_SERVICE_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


APP_CONFIG: dict[str, Any] = {
    "title": "Company Search Service",
    "version": "1.0.0",
}
