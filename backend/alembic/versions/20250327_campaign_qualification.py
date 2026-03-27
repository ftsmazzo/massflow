"""campaign qualification: config, sessions e respostas

Revision ID: 20250327_011
Revises: 20250326_010
Create Date: 2026-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250327_011"
down_revision: Union[str, None] = "20250326_010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_qualification_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("questions_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("scoring_rules_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("classification_rules_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("final_webhook_url", sa.String(length=1000), nullable=True),
        sa.Column("notify_lawyer", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "campaign_id", name="uq_qualification_config_tenant_campaign"),
    )
    op.create_index("ix_campaign_qualification_configs_tenant_id", "campaign_qualification_configs", ["tenant_id"])
    op.create_index("ix_campaign_qualification_configs_campaign_id", "campaign_qualification_configs", ["campaign_id"])

    op.create_table(
        "campaign_qualification_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_phone", sa.String(length=30), nullable=False),
        sa.Column("lead_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="in_progress"),
        sa.Column("current_step", sa.String(length=20), nullable=True),
        sa.Column("answers_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("score_total", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("classification", sa.String(length=60), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notified_at", sa.DateTime(), nullable=True),
        sa.Column("final_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaign_qualification_sessions_tenant_id", "campaign_qualification_sessions", ["tenant_id"])
    op.create_index("ix_campaign_qualification_sessions_campaign_id", "campaign_qualification_sessions", ["campaign_id"])
    op.create_index("ix_campaign_qualification_sessions_lead_id", "campaign_qualification_sessions", ["lead_id"])
    op.create_index("ix_campaign_qualification_sessions_lead_phone", "campaign_qualification_sessions", ["lead_phone"])
    op.create_index("ix_campaign_qualification_sessions_status", "campaign_qualification_sessions", ["status"])

    op.create_table(
        "campaign_qualification_answers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("campaign_qualification_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_key", sa.String(length=20), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("answer_raw", sa.Text(), nullable=False),
        sa.Column("normalized_answer", sa.String(length=255), nullable=True),
        sa.Column("score_delta", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("answer_meta", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaign_qualification_answers_session_id", "campaign_qualification_answers", ["session_id"])
    op.create_index("ix_campaign_qualification_answers_step_key", "campaign_qualification_answers", ["step_key"])


def downgrade() -> None:
    op.drop_index("ix_campaign_qualification_answers_step_key", table_name="campaign_qualification_answers")
    op.drop_index("ix_campaign_qualification_answers_session_id", table_name="campaign_qualification_answers")
    op.drop_table("campaign_qualification_answers")

    op.drop_index("ix_campaign_qualification_sessions_status", table_name="campaign_qualification_sessions")
    op.drop_index("ix_campaign_qualification_sessions_lead_phone", table_name="campaign_qualification_sessions")
    op.drop_index("ix_campaign_qualification_sessions_lead_id", table_name="campaign_qualification_sessions")
    op.drop_index("ix_campaign_qualification_sessions_campaign_id", table_name="campaign_qualification_sessions")
    op.drop_index("ix_campaign_qualification_sessions_tenant_id", table_name="campaign_qualification_sessions")
    op.drop_table("campaign_qualification_sessions")

    op.drop_index("ix_campaign_qualification_configs_campaign_id", table_name="campaign_qualification_configs")
    op.drop_index("ix_campaign_qualification_configs_tenant_id", table_name="campaign_qualification_configs")
    op.drop_table("campaign_qualification_configs")
