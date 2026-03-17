"""
Modelo Tag (para funis e segmentação)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base
from app.models.associations import lead_tags


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("Lead", secondary=lead_tags, back_populates="tags")

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_tag_tenant_name"),)
