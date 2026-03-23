"""
Respostas de leads recebidas via Evolution (webhook inbound), atribuídas à última campanha que disparou.
Persistidas no MassFlow mesmo sem URL do n8n — o encaminhamento externo é opcional.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from datetime import datetime

from app.database import Base


class CampaignInboundReply(Base):
    __tablename__ = "campaign_inbound_replies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    # Instância Evolution (número) em que a resposta foi recebida — alinhado ao CampaignMessage.evolution_instance_id do disparo
    evolution_instance_id = Column(Integer, ForeignKey("evolution_instances.id", ondelete="SET NULL"), nullable=True, index=True)

    message_text = Column(Text, nullable=False)
    forwarded_to_webhook = Column(Boolean, nullable=False, default=False)
    webhook_skip_reason = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
