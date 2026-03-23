"""campaign_inbound_replies.evolution_instance_id

Revision ID: 20250324_008
Revises: 20250323_007
Create Date: 2025-03-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20250324_008"
down_revision: Union[str, None] = "20250323_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "campaign_inbound_replies",
        sa.Column("evolution_instance_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_campaign_inbound_replies_evolution_instance_id",
        "campaign_inbound_replies",
        "evolution_instances",
        ["evolution_instance_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_campaign_inbound_replies_evolution_instance_id",
        "campaign_inbound_replies",
        ["evolution_instance_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_campaign_inbound_replies_evolution_instance_id", table_name="campaign_inbound_replies")
    op.drop_constraint("fk_campaign_inbound_replies_evolution_instance_id", "campaign_inbound_replies", type_="foreignkey")
    op.drop_column("campaign_inbound_replies", "evolution_instance_id")
