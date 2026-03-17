"""evolution_instances table

Revision ID: 20250306_002
Revises: 20250306_001
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250306_002"
down_revision: Union[str, None] = "20250306_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evolution_instances",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("api_url", sa.String(500), nullable=False),
        sa.Column("api_key", sa.String(255), server_default=sa.text("''")),
        sa.Column("display_name", sa.String(255)),
        sa.Column("owner", sa.String(20), nullable=False, server_default=sa.text("'tenant'")),
        sa.Column("status", sa.String(50), server_default=sa.text("'created'")),
        sa.Column("limits", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("last_health_at", sa.DateTime()),
    )
    op.create_index("ix_evolution_instances_tenant_id", "evolution_instances", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_evolution_instances_tenant_id", table_name="evolution_instances")
    op.drop_table("evolution_instances")
