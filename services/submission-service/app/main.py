import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.routes import admin as admin_routes
from .api.routes import submissions as submission_routes
from .core.database import Base, database_ready, engine
from .core.observability import RequestContextMiddleware, configure_logging
from .core.settings import settings
from .services.photo_storage import ensure_bucket_exists

configure_logging(settings.log_level, settings.json_logs)
logger = logging.getLogger(settings.service_name)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Submission Service",
        version="1.0.0",
        description=(
            "Accepts submissions (photo + metadata), classifies the "
            "photo, stores it, and serves admin search/filter queries. Requests "
            "are authenticated by verifying JWTs minted by the auth service."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_credentials=False,  # the platform authenticates with bearer tokens, not cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Added last so it wraps everything (request id is set before other layers).
    app.add_middleware(RequestContextMiddleware, logger_name=settings.service_name)

    app.state.limiter = submission_routes.rate_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(submission_routes.router, prefix="/submissions")
    app.include_router(admin_routes.router, prefix="/admin")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness: process is up. Kept cheap so a slow DB never kills the pod."""
        return {"status": "ok", "service": settings.service_name}

    @app.get("/health/ready", tags=["meta"])
    def readiness():
        """Readiness: only serve traffic when the database is reachable."""
        if database_ready():
            return {"status": "ready", "service": settings.service_name}
        return JSONResponse(
            status_code=503, content={"status": "not-ready", "service": settings.service_name}
        )

    @app.on_event("startup")
    def on_startup() -> None:
        # Alembic owns the schema in real deployments (run as a one-off Job);
        # create_all only runs when AUTO_CREATE_SCHEMA is set (dev convenience).
        if settings.auto_create_schema:
            Base.metadata.create_all(bind=engine)
        try:
            ensure_bucket_exists()
        except Exception as exc:
            # Storage may not be ready yet; the first request retries.
            logger.warning("bucket bootstrap failed: %s", exc)

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        engine.dispose()

    return app


app = create_application()
