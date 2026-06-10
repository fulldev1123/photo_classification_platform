import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.routes import admin as admin_routes
from .api.routes import submissions as submission_routes
from .core.database import Base, engine
from .core.settings import settings
from .services.photo_storage import ensure_bucket_exists

logging.basicConfig(level=settings.log_level)
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

    app.state.limiter = submission_routes.rate_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(submission_routes.router, prefix="/submissions")
    app.include_router(admin_routes.router, prefix="/admin")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        try:
            ensure_bucket_exists()
        except Exception as exc:
            # Storage may not be ready yet; the first request retries and the
            # readiness probe keeps traffic away until then.
            logger.warning("bucket bootstrap failed: %s", exc)

    return app


app = create_application()
