import io
import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
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
rate_limiter = Limiter(key_func=get_remote_address)

_ACCEPTED_CONTENT_TYPES = {
    t.strip() for t in settings.allowed_image_types.split(",") if t.strip()
}


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
async def create_submission(
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

    content = await photo.read()
    enforce_upload_policy(content, photo.content_type or "")

    classification = classify_photo(content)

    content_type = photo.content_type or "application/octet-stream"
    photo_key = f"{user.id}/{uuid.uuid4()}-{photo.filename or 'photo'}"
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
    summary="List the caller's own submissions",
)
def list_my_submissions(
    session: Session = Depends(get_session),
    user: AuthenticatedUser = Depends(get_authenticated_user),
):
    submissions = SubmissionRepository(session).list_for_owner(user.id)
    return [serialize_submission(submission) for submission in submissions]
