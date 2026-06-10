import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ...core.database import get_session
from ...core.security import AuthenticatedUser, require_administrator
from ...core.settings import settings
from ...models import Gender
from ...repositories import SubmissionRepository, SubmissionSearchFilters
from ...schemas import PaginatedSubmissions, SubmissionWithPhotoUrl
from ..serializers import serialize_submission

router = APIRouter(tags=["admin"])
rate_limiter = Limiter(
    key_func=get_remote_address, storage_uri=settings.rate_limit_storage_uri
)


@router.get(
    "/submissions",
    response_model=PaginatedSubmissions,
    summary="List and filter submissions (admin only)",
)
@rate_limiter.limit(settings.admin_list_rate_limit)
def list_submissions(
    request: Request,
    min_age: int | None = Query(None, ge=0, le=130),
    max_age: int | None = Query(None, ge=0, le=130),
    gender: Gender | None = None,
    country_of_origin: str | None = Query(None, max_length=80),
    residence: str | None = Query(None, max_length=160),
    name: str | None = Query(None, max_length=120, description="Substring of the full name"),
    classification_label: str | None = Query(None, max_length=80),
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    session: Session = Depends(get_session),
    _: AuthenticatedUser = Depends(require_administrator),
):
    filters = SubmissionSearchFilters(
        min_age=min_age,
        max_age=max_age,
        gender=gender,
        country_of_origin=country_of_origin,
        residence=residence,
        name_query=name,
        classification_label=classification_label,
        created_after=created_after,
        created_before=created_before,
    )
    submissions, total = SubmissionRepository(session).search(filters, page, page_size)
    return PaginatedSubmissions(
        items=[serialize_submission(submission) for submission in submissions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionWithPhotoUrl,
    summary="Retrieve a single submission (admin only)",
)
def get_submission(
    submission_id: uuid.UUID,
    session: Session = Depends(get_session),
    _: AuthenticatedUser = Depends(require_administrator),
):
    submission = SubmissionRepository(session).get(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="not found")
    return serialize_submission(submission)
