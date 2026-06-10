import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.routes import auth as auth_routes
from .bootstrap import seed_admin_account
from .core.database import Base, database_ready, engine
from .core.observability import RequestContextMiddleware, configure_logging
from .core.settings import settings

configure_logging(settings.log_level, settings.json_logs)
logger = logging.getLogger(settings.service_name)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Auth Service",
        version="1.0.0",
        description="User registration, login, and JWT issuance for the photo platform.",
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

    app.state.limiter = auth_routes.rate_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(auth_routes.router, prefix="/auth")

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
        seed_admin_account()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        engine.dispose()

    return app


app = create_application()
