import uvicorn

from app.config import Settings
from app.logging_config import configure_logging


def main() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_config=None,
        log_level=settings.log_level,
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
        server_header=False,
        timeout_graceful_shutdown=settings.graceful_shutdown_timeout,
    )


if __name__ == "__main__":
    main()
