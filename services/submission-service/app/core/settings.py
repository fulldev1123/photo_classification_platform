from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the submission service.

    Every field maps to an upper-cased environment variable of the same name.
    Defaults target the local Docker Compose topology.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Service ---
    service_name: str = "submission-service"
    log_level: str = "INFO"
    cors_origins: str = "*"

    # --- Database ---
    database_url: str = "postgresql+psycopg2://submission:submission@submission-db:5432/submission_db"

    # --- Shared JWT secret with the auth service (stateless validation) ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # --- Object storage (S3-compatible: MinIO / AWS S3) ---
    s3_endpoint_url: str | None = "http://minio:9000"
    # Endpoint used when signing URLs handed back to the browser. In Docker/K8s
    # the in-cluster endpoint above is unreachable from the user's browser, so
    # this should be the externally-resolvable host. Falls back to the internal
    # endpoint when unset.
    s3_public_endpoint_url: str | None = None
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "photos"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    s3_force_path_style: bool = True
    s3_presigned_expires: int = 3600  # seconds

    # --- Upload safety policy ---
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    min_image_pixels: int = 64 * 64
    max_image_pixels: int = 4096 * 4096

    # --- Abuse protection (per-client request quotas) ---
    submit_rate_limit: str = "20/minute"
    admin_list_rate_limit: str = "60/minute"


settings = Settings()
