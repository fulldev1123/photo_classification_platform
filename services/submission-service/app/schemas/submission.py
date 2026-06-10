import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models import Gender


class SubmissionMetadata(BaseModel):
    """Validated metadata fields that accompany a photo submission."""

    full_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    residence: str = Field(min_length=1, max_length=160)
    gender: Gender
    country_of_origin: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=2000)


class SubmissionResponse(BaseModel):
    """Full submission record returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    full_name: str
    age: int
    residence: str
    gender: Gender
    country_of_origin: str
    description: str | None

    photo_key: str
    photo_content_type: str
    photo_size_bytes: int

    classification_label: str
    classification_score: int
    classification_meta: dict

    created_at: datetime
    updated_at: datetime


class SubmissionWithPhotoUrl(SubmissionResponse):
    """A submission plus a short-lived presigned URL for its photo."""

    photo_url: str = ""


class PaginatedSubmissions(BaseModel):
    """A page of submissions for the admin listing endpoint."""

    items: list[SubmissionWithPhotoUrl]
    total: int
    page: int
    page_size: int
