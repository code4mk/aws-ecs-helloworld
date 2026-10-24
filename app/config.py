import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    build_sha: str
    message: str
    host: str
    port: int
    log_level: str
    log_health_checks: bool
    metadata_timeout: float
    graceful_shutdown_timeout: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "aws-ecs-helloworld"),
            app_version=os.getenv("APP_VERSION", "dev"),
            build_sha=os.getenv("BUILD_SHA", "unknown"),
            message=os.getenv("MESSAGE", "Your Amazon ECS app is live"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            log_health_checks=_env_bool("LOG_HEALTH_CHECKS", False),
            metadata_timeout=float(os.getenv("ECS_METADATA_TIMEOUT", "2")),
            graceful_shutdown_timeout=int(os.getenv("GRACEFUL_SHUTDOWN_TIMEOUT", "20")),
        )
