"""campaign_inbound_replies — respostas persistidas no MassFlow (webhook n8n opcional)

Revision ID: 20250323_007
Revises: 20250306_006
Create Date: 2025-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250323_007"
down_revision: Union[str, None] = "20250306_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_inbound_replies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("forwarded_to_webhook", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("webhook_skip_reason", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaign_inbound_replies_tenant_id", "campaign_inbound_replies", ["tenant_id"])
    op.create_index("ix_campaign_inbound_replies_campaign_id", "campaign_inbound_replies", ["campaign_id"])
    op.create_index("ix_campaign_inbound_replies_lead_id", "campaign_inbound_replies", ["lead_id"])
    op.create_index("ix_campaign_inbound_replies_created_at", "campaign_inbound_replies", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_campaign_inbound_replies_created_at", table_name="campaign_inbound_replies")
    op.drop_index("ix_campaign_inbound_replies_lead_id", table_name="campaign_inbound_replies")
    op.drop_index("ix_campaign_inbound_replies_campaign_id", table_name="campaign_inbound_replies")
    op.drop_index("ix_campaign_inbound_replies_tenant_id", table_name="campaign_inbound_replies")
    op.drop_table("campaign_inbound_replies")
