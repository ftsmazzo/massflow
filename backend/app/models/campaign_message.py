"""
Registro de cada envio de campanha (para rastreio e histórico).
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from app.database import Base


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    evolution_instance_id = Column(Integer, ForeignKey("evolution_instances.id", ondelete="SET NULL"), nullable=True)

    # ID da mensagem retornado pela Evolution API
    message_id = Column(String(255), nullable=True)
    status = Column(String(50), default="pending")  # pending | sent | failed
    error_message = Column(String(500), nullable=True)
    sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
