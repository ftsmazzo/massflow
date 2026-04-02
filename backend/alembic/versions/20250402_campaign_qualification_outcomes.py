"""campaign_qualification_outcomes: snapshot por sessão concluída (analytics / N8N)

Revision ID: 20250402_014
Revises: 20250329_013
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250402_014"
down_revision: Union[str, None] = "20250329_013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_qualification_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("campaign_qualification_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campaign_name", sa.String(length=255), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_phone", sa.String(length=30), nullable=False),
        sa.Column("lead_name", sa.String(length=255), nullable=True),
        sa.Column("score_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("classification", sa.String(length=60), nullable=True),
        sa.Column("notify_lawyer", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "answers_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "payload_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("session_id", name="uq_campaign_qualification_outcomes_session_id"),
    )
    op.create_index(
        "ix_campaign_qualification_outcomes_tenant_id",
        "campaign_qualification_outcomes",
        ["tenant_id"],
    )
    op.create_index(
        "ix_campaign_qualification_outcomes_campaign_id",
        "campaign_qualification_outcomes",
        ["campaign_id"],
    )
    op.create_index(
        "ix_campaign_qualification_outcomes_lead_id",
        "campaign_qualification_outcomes",
        ["lead_id"],
    )
    op.create_index(
        "ix_campaign_qualification_outcomes_lead_phone",
        "campaign_qualification_outcomes",
        ["lead_phone"],
    )
    op.create_index(
        "ix_campaign_qualification_outcomes_tenant_campaign",
        "campaign_qualification_outcomes",
        ["tenant_id", "campaign_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_qualification_outcomes_tenant_campaign", table_name="campaign_qualification_outcomes")
    op.drop_index("ix_campaign_qualification_outcomes_lead_phone", table_name="campaign_qualification_outcomes")
    op.drop_index("ix_campaign_qualification_outcomes_lead_id", table_name="campaign_qualification_outcomes")
    op.drop_index("ix_campaign_qualification_outcomes_campaign_id", table_name="campaign_qualification_outcomes")
    op.drop_index("ix_campaign_qualification_outcomes_tenant_id", table_name="campaign_qualification_outcomes")
    op.drop_table("campaign_qualification_outcomes")
