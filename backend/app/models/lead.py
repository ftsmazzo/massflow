"""
Modelo Lead (contato do tenant)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.database import Base
from app.models.associations import list_leads, lead_tags


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    name = Column(String(255))
    email = Column(String(255))

    # Campos custom (JSON); opt-in para receber disparos
    custom_fields = Column(JSONB, default=dict)
    opt_in = Column(Boolean, default=True)

    # Status: ativo, na_esteira, opt_out, etc.
    status = Column(String(50), default="ativo")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sent_at = Column(DateTime, nullable=True)
    last_response_at = Column(DateTime, nullable=True)

    lists = relationship("List", secondary=list_leads, back_populates="leads")
    tags = relationship("Tag", secondary=lead_tags, back_populates="leads")

    __table_args__ = (UniqueConstraint("tenant_id", "phone", name="uq_lead_tenant_phone"),)
