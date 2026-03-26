"""reception_contexts.consumed_at para uso único no agente

Revision ID: 20250326_010
Revises: 20250326_009
Create Date: 2025-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250326_010"
down_revision: Union[str, None] = "20250326_009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reception_contexts", sa.Column("consumed_at", sa.DateTime(), nullable=True))
    op.create_index("ix_reception_contexts_consumed_at", "reception_contexts", ["consumed_at"])


def downgrade() -> None:
    op.drop_index("ix_reception_contexts_consumed_at", table_name="reception_contexts")
    op.drop_column("reception_contexts", "consumed_at")
