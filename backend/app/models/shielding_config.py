"""
Configuração global de blindagem por tenant (evitar e mitigar banimentos).
Uma linha por tenant; config em JSONB para flexibilidade e evolução sem novas migrações.
"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class TenantShieldingConfig(Base):
    __tablename__ = "tenant_shielding_config"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(
        Integer,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    config = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", backref="shielding_config")
