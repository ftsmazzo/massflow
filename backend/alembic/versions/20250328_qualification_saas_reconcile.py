"""qualification: config reconciliação SaaS chatMessages + notificação WhatsApp

Revision ID: 20250328_012
Revises: 20250327_011
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250328_012"
down_revision: Union[str, None] = "20250327_011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign_qualification_configs",
        sa.Column(
            "reconcile_from_saas_chat",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "campaign_qualification_configs",
        sa.Column("saas_tenant_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "campaign_qualification_configs",
        sa.Column("reconcile_notify_phone", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "campaign_qualification_configs",
        sa.Column(
            "reconcile_notify_instance_id",
            sa.Integer(),
            sa.ForeignKey("evolution_instances.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("campaign_qualification_configs", "reconcile_notify_instance_id")
    op.drop_column("campaign_qualification_configs", "reconcile_notify_phone")
    op.drop_column("campaign_qualification_configs", "saas_tenant_id")
    op.drop_column("campaign_qualification_configs", "reconcile_from_saas_chat")
