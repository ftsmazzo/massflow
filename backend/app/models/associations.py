"""
Tabelas de associação many-to-many
"""
from sqlalchemy import Table, Column, Integer, ForeignKey, UniqueConstraint
from app.database import Base

list_leads = Table(
    "list_leads",
    Base.metadata,
    Column("list_id", Integer, ForeignKey("lists.id", ondelete="CASCADE"), primary_key=True),
    Column("lead_id", Integer, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
)

lead_tags = Table(
    "lead_tags",
    Base.metadata,
    Column("lead_id", Integer, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)
