import logging
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from ..core.settings import settings

logger = logging.getLogger(__name__)


def _build_client(endpoint_url: str | None):
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"},
            # Fail fast on a slow/unavailable object store instead of pinning a
            # worker for botocore's default 60s timeouts and ~5 legacy retries.
            connect_timeout=settings.s3_connect_timeout,
            read_timeout=settings.s3_read_timeout,
            retries={"max_attempts": settings.s3_max_attempts, "mode": "standard"},
        ),
    )


@lru_cache(maxsize=1)
def internal_s3_client():
    """Client bound to the in-cluster endpoint (uploads, bucket management)."""
    return _build_client(settings.s3_endpoint_url)


@lru_cache(maxsize=1)
def public_s3_client():
    """Client bound to the browser-reachable endpoint, used only to sign the
    download URLs the user's browser will fetch directly."""
    return _build_client(settings.s3_public_endpoint_url or settings.s3_endpoint_url)


def ensure_bucket_exists() -> None:
    """Create the photo bucket on first run if it is not already present."""
    client = internal_s3_client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except ClientError:
        logger.info("creating bucket %s", settings.s3_bucket)
        try:
            client.create_bucket(Bucket=settings.s3_bucket)
        except ClientError as exc:
            logger.warning("create_bucket failed: %s", exc)


def upload_photo(key: str, body: bytes, content_type: str) -> None:
    """Store a photo object under ``key`` in the private bucket."""
    internal_s3_client().put_object(
        Bucket=settings.s3_bucket, Key=key, Body=body, ContentType=content_type
    )


def generate_presigned_download_url(key: str, expires: int | None = None) -> str:
    """Return a time-limited URL that grants read access to one object."""
    return public_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires or settings.s3_presigned_expires,
    )
