from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the auth service.

    Every field maps to an upper-cased environment variable of the same name
    (e.g. ``database_url`` <- ``DATABASE_URL``). Defaults target the local
    Docker Compose topology.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Service ---
    service_name: str = "auth-service"
    log_level: str = "INFO"
    cors_origins: str = "*"  # comma-separated allow-list; restrict in prod

    # --- Database ---
    database_url: str = "postgresql+psycopg2://auth:auth@auth-db:5432/auth_db"

    # --- JSON Web Tokens ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60

    # --- Bootstrap administrator (seeded on first start if absent) ---
    admin_email: str = "admin@example.com"
    admin_password: str = "admin12345"

    # --- Abuse protection (per-client request quotas) ---
    login_rate_limit: str = "10/minute"
    register_rate_limit: str = "5/minute"
    # "memory://" = per-pod (dev). For correct limits across HPA replicas use a
    # shared store, e.g. "redis://redis:6379/0" (requires the redis extra).
    rate_limit_storage_uri: str = "memory://"

    # --- Database connection pool ---
    # Size so max_replicas * (db_pool_size + db_max_overflow) stays below the
    # database's max_connections; front with PgBouncer for large replica counts.
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 10  # seconds to wait for a free connection (fail fast)
    db_pool_recycle: int = 1800  # recycle connections before infra idle cutoffs
    db_connect_timeout: int = 5  # psycopg2 TCP connect timeout (seconds)
    db_statement_timeout_ms: int = 15000  # server-side per-statement timeout

    # --- Observability ---
    json_logs: bool = True  # structured JSON logs carrying a request id

    # --- Schema bootstrap: Alembic owns the schema in real deployments;
    #     create_all only runs when this is True (dev convenience). ---
    auto_create_schema: bool = False


settings = Settings()
