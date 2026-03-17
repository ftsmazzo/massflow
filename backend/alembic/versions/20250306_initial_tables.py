"""initial tables: tenants, users, tags, lists, leads, list_leads, lead_tags

Revision ID: 20250306_001
Revises:
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250306_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("plan_type", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("credits_balance", sa.Integer(), server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("last_login", sa.DateTime()),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "name", name="uq_tag_tenant_name"),
    )
    op.create_index("ix_tags_tenant_id", "tags", ["tenant_id"])

    op.create_table(
        "lists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_lists_tenant_id", "lists", ["tenant_id"])

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("custom_fields", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("opt_in", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("status", sa.String(50), server_default=sa.text("'ativo'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("last_sent_at", sa.DateTime()),
        sa.Column("last_response_at", sa.DateTime()),
        sa.UniqueConstraint("tenant_id", "phone", name="uq_lead_tenant_phone"),
    )
    op.create_index("ix_leads_tenant_id", "leads", ["tenant_id"])

    op.create_table(
        "list_leads",
        sa.Column("list_id", sa.Integer(), sa.ForeignKey("lists.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "lead_tags",
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("lead_tags")
    op.drop_table("list_leads")
    op.drop_table("leads")
    op.drop_table("lists")
    op.drop_table("tags")
    op.drop_table("users")
    op.drop_table("tenants")
