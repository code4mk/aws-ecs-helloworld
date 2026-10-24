import html
import logging
import socket
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import Settings
from app.metadata import EcsMetadata, fetch_ecs_metadata

logger = logging.getLogger("app")

HEALTH_PATHS = {"/health", "/ready"}
INDEX_TEMPLATE = Template((Path(__file__).parent / "templates" / "index.html").read_text())

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}
INDEX_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    hostname = socket.gethostname()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.started_at = time.time()
        app.state.metadata = await fetch_ecs_metadata(settings.metadata_timeout)
        app.state.ready = True
        logger.info(
            "Application started",
            extra={"version": settings.app_version, "port": settings.port, "on_ecs": app.state.metadata is not None},
        )
        yield
        app.state.ready = False
        logger.info("Application shutting down")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Hello World sample container for Amazon ECS.",
        lifespan=lifespan,
    )
    app.state.ready = False

    def runtime_info(request: Request) -> dict[str, Any]:
        metadata: EcsMetadata | None = request.app.state.metadata
        return {
            "app": {
                "name": settings.app_name,
                "version": settings.app_version,
                "build_sha": settings.build_sha,
                "message": settings.message,
            },
            "runtime": {
                "hostname": hostname,
                "uptime_seconds": int(time.time() - request.app.state.started_at),
                "server_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            "ecs": metadata.to_dict() if metadata else None,
        }

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error", extra={"request_id": request_id, "path": request.url.path})
            response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)

        response.headers["X-Request-ID"] = request_id
        response.headers.update(SECURITY_HEADERS)

        if settings.log_health_checks or request.url.path not in HEALTH_PATHS:
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent"),
                },
            )
        return response

    @app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request) -> HTMLResponse:
        on_ecs = request.app.state.metadata is not None
        page = INDEX_TEMPLATE.safe_substitute(
            title=html.escape(settings.app_name),
            message=html.escape(settings.message),
            env_badge="Running on Amazon ECS" if on_ecs else "Running locally",
            env_class="ecs" if on_ecs else "local",
        )
        return HTMLResponse(page, headers={"Content-Security-Policy": INDEX_CSP, "Cache-Control": "no-store"})

    @app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
    async def health() -> dict[str, str]:
        """Liveness: the process is up and serving requests. Use for ALB target group and container health checks."""
        return {"status": "healthy"}

    @app.api_route("/ready", methods=["GET", "HEAD"], tags=["health"])
    async def ready(request: Request) -> JSONResponse:
        """Readiness: startup finished and the app is not shutting down."""
        if request.app.state.ready:
            return JSONResponse({"status": "ready"})
        return JSONResponse({"status": "not_ready"}, status_code=503)

    @app.get("/api/info", tags=["info"])
    async def info(request: Request) -> dict[str, Any]:
        """Application, runtime and ECS task details as JSON."""
        return runtime_info(request)

    return app


app = create_app()
