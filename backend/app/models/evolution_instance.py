"""
Modelo EvolutionInstance (instância WhatsApp - Evolution API)
Respeita nível da conta: owner=tenant (própria) ou owner=platform (plataforma).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class EvolutionInstance(Base):
    __tablename__ = "evolution_instances"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Nome na Evolution API (instanceName) - único por servidor
    name = Column(String(100), nullable=False)
    # URL base da Evolution (ex: https://evolution.seudominio.com)
    api_url = Column(String(500), nullable=False)
    # API key / token da Evolution (header apikey)
    api_key = Column(String(255), default="")

    # Nome amigável na UI
    display_name = Column(String(255))

    # owner: "tenant" = instância do cliente; "platform" = instância da plataforma
    owner = Column(String(20), nullable=False, default="tenant")

    # Status local (espelhado da Evolution): created, connecting, open, close, etc.
    status = Column(String(50), default="created")

    # Limites opcionais (mensagens/hora, etc.) - JSON
    limits = Column(JSONB, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_health_at = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", backref="evolution_instances")
