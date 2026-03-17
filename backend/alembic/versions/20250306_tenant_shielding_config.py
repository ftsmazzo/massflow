"""tenant_shielding_config - configuração global de blindagem por tenant

Revision ID: 20250306_004
Revises: 20250306_003
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250306_004"
down_revision: Union[str, None] = "20250306_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_shielding_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_tenant_shielding_config_tenant_id", "tenant_shielding_config", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tenant_shielding_config_tenant_id", table_name="tenant_shielding_config")
    op.drop_table("tenant_shielding_config")
