"""
Snapshot do fluxo n8n (recepção) para contexto do agente na próxima mensagem.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.database import Base


class ReceptionContext(Base):
    __tablename__ = "reception_contexts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    lead_phone = Column(String(30), nullable=False, index=True)
    lead_name = Column(String(255), nullable=True)
    mensagem_lead = Column(Text, nullable=True)
    campanha = Column(String(255), nullable=True)
    msg_campanha = Column(Text, nullable=True)
    msg_recepcao = Column(Text, nullable=True)

    payload = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    consumed_at = Column(DateTime, nullable=True, index=True)
