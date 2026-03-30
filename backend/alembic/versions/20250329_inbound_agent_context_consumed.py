"""campaign_inbound_replies: sinal agent_context_consumed (agente consumiu contexto de recepção)

Revision ID: 20250329_013
Revises: 20250328_012
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250329_013"
down_revision: Union[str, None] = "20250328_012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign_inbound_replies",
        sa.Column(
            "agent_context_consumed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("campaign_inbound_replies", "agent_context_consumed")
