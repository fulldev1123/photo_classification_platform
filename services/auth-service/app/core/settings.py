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


settings = Settings()
