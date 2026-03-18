"""campaigns table

Revision ID: 20250306_005
Revises: 20250306_004
Create Date: 2025-03-06

Aplicada automaticamente na implantação (Easypanel); não rodar migrações no terminal.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250306_005"
down_revision: Union[str, None] = "20250306_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), server_default=sa.text("'immediate'")),
        sa.Column("list_id", sa.Integer(), sa.ForeignKey("lists.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tag_filter_include", postgresql.JSONB(), nullable=True),
        sa.Column("tag_filter_exclude", postgresql.JSONB(), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("use_global_shielding", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("shielding_override", postgresql.JSONB(), nullable=True),
        sa.Column("instance_ids", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(50), server_default=sa.text("'draft'")),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaigns_tenant_id", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_list_id", "campaigns", ["list_id"])
    op.create_index("ix_campaigns_status", "campaigns", ["status"])


def downgrade() -> None:
    op.drop_index("ix_campaigns_status", table_name="campaigns")
    op.drop_index("ix_campaigns_list_id", table_name="campaigns")
    op.drop_index("ix_campaigns_tenant_id", table_name="campaigns")
    op.drop_table("campaigns")
