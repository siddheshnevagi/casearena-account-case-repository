"""case_files: PDF bytes stored in the database

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-28

Supports STORAGE_BACKEND=database (see app/services/storage.py and
ARCHITECTURE.md ADR-07). Creating this table is harmless when another
storage backend is configured — it simply stays empty.

Hand-written, like 0001, to mirror app/models/case_file.py exactly.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_case_files_storage_key", "case_files", ["storage_key"])


def downgrade() -> None:
    op.drop_index("ix_case_files_storage_key", table_name="case_files")
    op.drop_table("case_files")
