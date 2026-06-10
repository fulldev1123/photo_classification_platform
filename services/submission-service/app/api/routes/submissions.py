import io
import logging
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.security import AuthenticatedUser, get_authenticated_user
from ...core.settings import settings
from ...models import Gender, Submission
from ...repositories import SubmissionRepository
from ...schemas import SubmissionMetadata, SubmissionWithPhotoUrl
from ...services.classifier import classify_photo
from ...services.photo_storage import upload_photo
from ..serializers import serialize_submission

logger = logging.getLogger(__name__)
router = APIRouter(tags=["submissions"])
rate_limiter = Limiter(
    key_func=get_remote_address, storage_uri=settings.rate_limit_storage_uri
)

_ACCEPTED_CONTENT_TYPES = {
    t.strip() for t in settings.allowed_image_types.split(",") if t.strip()
}


def _read_upload(photo: UploadFile, max_bytes: int) -> bytes:
    """Read the upload in bounded chunks, aborting with 413 the moment the
    running total exceeds the cap — so an oversized body is rejected mid-stream
    instead of being fully buffered into memory."""
    chunks: list[bytes] = []
    total = 0
    source = photo.file  # underlying SpooledTemporaryFile (sync)
    while True:
        chunk = source.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413, detail=f"file too large; max {max_bytes} bytes"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _safe_filename(name: str | None) -> str:
    """Strip path components and unusual characters from the client filename
    before embedding it in the object key."""
    base = (name or "photo").replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(c for c in base if c.isalnum() or c in "._-")
    return (cleaned or "photo")[:100]


def enforce_upload_policy(content: bytes, content_type: str) -> tuple[int, int]:
    """Apply upload safety rules and return the image's ``(width, height)``.

    1. Content-Type must be in the allow-list (rejects non-images with 415).
    2. Size must not exceed ``max_upload_bytes`` (413).
    3. Bytes must decode as a real image (defends against MIME spoofing).
    4. Pixel dimensions must stay within bounds (defends against
       decompression-bomb DoS from tiny files that explode in memory).
    """
    if content_type not in _ACCEPTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"unsupported content-type: {content_type}")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413, detail=f"file too large; max {settings.max_upload_bytes} bytes"
        )
    try:
        with Image.open(io.BytesIO(content)) as probe:
            probe.verify()  # verify() consumes the file object...
        with Image.open(io.BytesIO(content)) as probe:
            width, height = probe.size  # ...so re-open to read the dimensions
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="not a valid image") from exc

    pixel_count = width * height
    if pixel_count < settings.min_image_pixels:
        raise HTTPException(status_code=400, detail="image too small")
    if pixel_count > settings.max_image_pixels:
        raise HTTPException(status_code=400, detail="image too large (pixels)")
    return width, height


@router.post(
    "",
    response_model=SubmissionWithPhotoUrl,
    status_code=status.HTTP_201_CREATED,
    summary="Create a submission (photo + metadata)",
)
@rate_limiter.limit(settings.submit_rate_limit)
def create_submission(
    request: Request,
    full_name: str = Form(...),
    age: int = Form(...),
    residence: str = Form(...),
    gender: Gender = Form(...),
    country_of_origin: str = Form(...),
    description: str | None = Form(None),
    photo: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    # Sync handler: FastAPI runs it in a threadpool, so the blocking image
    # decode + classify + S3 upload + DB commit never stall the event loop.
    try:
        metadata = SubmissionMetadata(
            full_name=full_name,
            age=age,
            residence=residence,
            gender=gender,
            country_of_origin=country_of_origin,
            description=description,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    content = _read_upload(photo, settings.max_upload_bytes)
    enforce_upload_policy(content, photo.content_type or "")

    classification = classify_photo(content)

    content_type = photo.content_type or "application/octet-stream"
    photo_key = f"{user.id}/{uuid.uuid4()}-{_safe_filename(photo.filename)}"
    upload_photo(photo_key, content, content_type)

    submission = SubmissionRepository(session).add(
        Submission(
            owner_id=user.id,
            full_name=metadata.full_name,
            age=metadata.age,
            residence=metadata.residence,
            gender=metadata.gender,
            country_of_origin=metadata.country_of_origin,
            description=metadata.description,
            photo_key=photo_key,
            photo_content_type=content_type,
            photo_size_bytes=len(content),
            classification_label=classification.label,
            classification_score=classification.score,
            classification_meta=classification.meta,
        )
    )
    return serialize_submission(submission)


@router.get(
    "/me",
    response_model=list[SubmissionWithPhotoUrl],
    summary="List the caller's own submissions (newest first, keyset-paginated)",
)
def list_my_submissions(
    limit: int = Query(default=settings.my_submissions_page_size, ge=1, le=200),
    before: datetime | None = Query(
        default=None,
        description="Keyset cursor: return submissions created strictly before this timestamp",
    ),
    session: Session = Depends(get_session),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    submissions = SubmissionRepository(session).list_for_owner(
        user.id, limit=limit, before=before
    )
    return [serialize_submission(submission) for submission in submissions]
