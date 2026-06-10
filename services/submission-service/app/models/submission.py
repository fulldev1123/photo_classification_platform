import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class Submission(Base):
    """A user submission: personal metadata, the stored photo reference, and
    the classification produced at submission time."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=False
    )

    # --- Submitted metadata ---
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    residence: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender_enum"), nullable=False, index=True
    )
    country_of_origin: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Stored photo reference ---
    photo_key: Mapped[str] = mapped_column(String(512), nullable=False)
    photo_content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    photo_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Classification result ---
    classification_label: Mapped[str] = mapped_column(String(80), nullable=False)
    classification_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0..100
    classification_meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Composite index aligned with the admin filter UI, plus a time index for
    # range queries / pagination.
    __table_args__ = (
        Index("ix_submissions_filters", "gender", "country_of_origin", "age"),
        Index("ix_submissions_created_at", "created_at"),
    )
