"""campaign_messages table

Revision ID: 20250306_006
Revises: 20250306_005
Create Date: 2025-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250306_006"
down_revision: Union[str, None] = "20250306_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evolution_instance_id", sa.Integer(), sa.ForeignKey("evolution_instances.id", ondelete="SET NULL"), nullable=True),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), server_default=sa.text("'pending'")),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_campaign_messages_campaign_id", "campaign_messages", ["campaign_id"])
    op.create_index("ix_campaign_messages_lead_id", "campaign_messages", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_campaign_messages_lead_id", table_name="campaign_messages")
    op.drop_index("ix_campaign_messages_campaign_id", table_name="campaign_messages")
    op.drop_table("campaign_messages")
