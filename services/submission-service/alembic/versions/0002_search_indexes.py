"""search indexes: pg_trgm GIN for substring filters on full_name / residence

Revision ID: 0002_search_indexes
Revises: 0001_init_submissions
Create Date: 2026-06-10
"""
from alembic import op


revision = "0002_search_indexes"
down_revision = "0001_init_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trigram GIN indexes let the admin `ILIKE '%term%'` filters on full_name
    # and residence use an index instead of sequentially scanning the whole
    # submissions table. pg_trgm is a trusted extension (creatable by the DB
    # owner without superuser on PG 13+).
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_submissions_full_name_trgm",
        "submissions",
        ["full_name"],
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_submissions_residence_trgm",
        "submissions",
        ["residence"],
        postgresql_using="gin",
        postgresql_ops={"residence": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_submissions_residence_trgm", table_name="submissions")
    op.drop_index("ix_submissions_full_name_trgm", table_name="submissions")
    # Leave the pg_trgm extension in place; other objects may rely on it.
