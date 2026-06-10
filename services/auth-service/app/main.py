import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .api.routes import auth as auth_routes
from .bootstrap import seed_admin_account
from .core.database import Base, engine
from .core.settings import settings

logging.basicConfig(level=settings.log_level)
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

    app.state.limiter = auth_routes.rate_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(auth_routes.router, prefix="/auth")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.service_name}

    @app.on_event("startup")
    def on_startup() -> None:
        # Alembic owns the schema in real deployments; create_all is an
        # idempotent safety net for local / dev runs.
        Base.metadata.create_all(bind=engine)
        seed_admin_account()

    return app


app = create_application()
