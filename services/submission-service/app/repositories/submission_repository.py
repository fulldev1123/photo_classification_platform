import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..models import Gender, Submission


@dataclass
class SubmissionSearchFilters:
    """Optional admin filters applied to the submissions listing."""

    min_age: int | None = None
    max_age: int | None = None
    gender: Gender | None = None
    country_of_origin: str | None = None
    residence: str | None = None
    name_query: str | None = None
    classification_label: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None


class SubmissionRepository:
    """Data-access boundary for the ``submissions`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, submission: Submission) -> Submission:
        self._session.add(submission)
        self._session.commit()
        self._session.refresh(submission)
        return submission

    def get(self, submission_id: uuid.UUID) -> Submission | None:
        return self._session.get(Submission, submission_id)

    def list_for_owner(self, owner_id: uuid.UUID, limit: int = 200) -> list[Submission]:
        statement = (
            select(Submission)
            .where(Submission.owner_id == owner_id)
            .order_by(Submission.created_at.desc())
            .limit(limit)
        )
        return list(self._session.execute(statement).scalars().all())

    def search(
        self, filters: SubmissionSearchFilters, page: int, page_size: int
    ) -> tuple[list[Submission], int]:
        """Return one page of filtered submissions plus the total match count."""
        filtered = self._apply_filters(select(Submission), filters)
        total = self._session.execute(
            select(func.count()).select_from(filtered.subquery())
        ).scalar_one()
        rows = (
            self._session.execute(
                filtered.order_by(Submission.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), total

    @staticmethod
    def _apply_filters(statement: Select, filters: SubmissionSearchFilters) -> Select:
        if filters.min_age is not None:
            statement = statement.where(Submission.age >= filters.min_age)
        if filters.max_age is not None:
            statement = statement.where(Submission.age <= filters.max_age)
        if filters.gender is not None:
            statement = statement.where(Submission.gender == filters.gender)
        if filters.country_of_origin:
            statement = statement.where(
                Submission.country_of_origin.ilike(filters.country_of_origin)
            )
        if filters.residence:
            statement = statement.where(Submission.residence.ilike(f"%{filters.residence}%"))
        if filters.name_query:
            statement = statement.where(Submission.full_name.ilike(f"%{filters.name_query}%"))
        if filters.classification_label:
            statement = statement.where(
                Submission.classification_label == filters.classification_label
            )
        if filters.created_after:
            statement = statement.where(Submission.created_at >= filters.created_after)
        if filters.created_before:
            statement = statement.where(Submission.created_at <= filters.created_before)
        return statement
