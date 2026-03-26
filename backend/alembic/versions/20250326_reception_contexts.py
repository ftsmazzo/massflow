"""reception_contexts — snapshot do payload n8n para contexto do agente (próxima mensagem)

Revision ID: 20250326_009
Revises: 20250324_008
Create Date: 2025-03-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20250326_009"
down_revision: Union[str, None] = "20250324_008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reception_contexts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_phone", sa.String(30), nullable=False),
        sa.Column("lead_name", sa.String(255), nullable=True),
        sa.Column("mensagem_lead", sa.Text(), nullable=True),
        sa.Column("campanha", sa.String(255), nullable=True),
        sa.Column("msg_campanha", sa.Text(), nullable=True),
        sa.Column("msg_recepcao", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_reception_contexts_tenant_id", "reception_contexts", ["tenant_id"])
    op.create_index("ix_reception_contexts_lead_id", "reception_contexts", ["lead_id"])
    op.create_index("ix_reception_contexts_campaign_id", "reception_contexts", ["campaign_id"])
    op.create_index("ix_reception_contexts_lead_phone", "reception_contexts", ["lead_phone"])
    op.create_index("ix_reception_contexts_created_at", "reception_contexts", ["created_at"])
    op.create_index(
        "ix_reception_contexts_tenant_phone_created",
        "reception_contexts",
        ["tenant_id", "lead_phone", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_reception_contexts_tenant_phone_created", table_name="reception_contexts")
    op.drop_index("ix_reception_contexts_created_at", table_name="reception_contexts")
    op.drop_index("ix_reception_contexts_lead_phone", table_name="reception_contexts")
    op.drop_index("ix_reception_contexts_campaign_id", table_name="reception_contexts")
    op.drop_index("ix_reception_contexts_lead_id", table_name="reception_contexts")
    op.drop_index("ix_reception_contexts_tenant_id", table_name="reception_contexts")
    op.drop_table("reception_contexts")
