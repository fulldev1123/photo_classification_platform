"""init submissions

Revision ID: 0001_init_submissions
Revises:
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_init_submissions"
down_revision = None
branch_labels = None
depends_on = None


gender_enum = postgresql.ENUM(
    "male", "female", "other", "prefer_not_to_say", name="gender_enum"
)


def upgrade() -> None:
    gender_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("residence", sa.String(160), nullable=False),
        sa.Column(
            "gender",
            postgresql.ENUM(name="gender_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("country_of_origin", sa.String(80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_key", sa.String(512), nullable=False),
        sa.Column("photo_content_type", sa.String(80), nullable=False),
        sa.Column("photo_size_bytes", sa.Integer(), nullable=False),
        sa.Column("classification_label", sa.String(80), nullable=False),
        sa.Column("classification_score", sa.Integer(), nullable=False),
        sa.Column(
            "classification_meta",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_submissions_owner_id", "submissions", ["owner_id"])
    op.create_index("ix_submissions_age", "submissions", ["age"])
    op.create_index("ix_submissions_gender", "submissions", ["gender"])
    op.create_index("ix_submissions_country_of_origin", "submissions", ["country_of_origin"])
    op.create_index("ix_submissions_residence", "submissions", ["residence"])
    op.create_index(
        "ix_submissions_filters",
        "submissions",
        ["gender", "country_of_origin", "age"],
    )
    op.create_index("ix_submissions_created_at", "submissions", ["created_at"])


def downgrade() -> None:
    for index_name in [
        "ix_submissions_created_at",
        "ix_submissions_filters",
        "ix_submissions_residence",
        "ix_submissions_country_of_origin",
        "ix_submissions_gender",
        "ix_submissions_age",
        "ix_submissions_owner_id",
    ]:
        op.drop_index(index_name, table_name="submissions")
    op.drop_table("submissions")
    gender_enum.drop(op.get_bind(), checkfirst=True)
