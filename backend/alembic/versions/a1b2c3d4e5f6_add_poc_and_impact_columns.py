"""add poc and impact columns to findings

Revision ID: a1b2c3d4e5f6
Revises: 967f19e8684e
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "967f19e8684e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("method", sa.String(), nullable=True))
    op.add_column("findings", sa.Column("parameter_type", sa.String(), nullable=True))
    op.add_column("findings", sa.Column("impact", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("steps_to_reproduce", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("poc_artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "poc_artifacts")
    op.drop_column("findings", "steps_to_reproduce")
    op.drop_column("findings", "impact")
    op.drop_column("findings", "parameter_type")
    op.drop_column("findings", "method")
