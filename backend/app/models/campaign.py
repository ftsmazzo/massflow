"""
Modelo Campaign (campanha de disparo em massa).
Vínculos: lista, blindagem (global ou override), instâncias.
Conteúdo em JSONB (tipo de mídia, texto, variáveis, etc.).
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # type: immediate | scheduled
    type = Column(String(50), default="immediate")

    # Público: uma lista; opcional filtro por tags (array de nomes)
    list_id = Column(Integer, ForeignKey("lists.id", ondelete="RESTRICT"), nullable=False)
    tag_filter_include = Column(JSONB, nullable=True)  # ex: ["quente", "interessado"] — enviar só quem tem alguma
    tag_filter_exclude = Column(JSONB, nullable=True)   # ex: ["opt_out"] — não enviar quem tem alguma

    # Conteúdo: tipo (text | image | video | audio | document), text (com variáveis), media_url, etc.
    content = Column(JSONB, nullable=False, default=dict)

    # Blindagem: usar global do tenant ou override por campanha
    use_global_shielding = Column(Boolean, default=True)
    shielding_override = Column(JSONB, nullable=True)  # se não usar global, campos opcionais aqui

    # Instâncias: null = todas do tenant; ou array de evolution_instance.id
    instance_ids = Column(JSONB, nullable=True)  # [1, 2] ou null para "todas"

    # Status: draft | scheduled | running | completed | cancelled
    status = Column(String(50), default="draft")

    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos (opcional para queries)
    # list = relationship("List", backref="campaigns")
