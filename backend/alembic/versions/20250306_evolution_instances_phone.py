"""add phone_number to evolution_instances

Revision ID: 20250306_003
Revises: 20250306_002
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250306_003"
down_revision: Union[str, None] = "20250306_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("evolution_instances", sa.Column("phone_number", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("evolution_instances", "phone_number")
