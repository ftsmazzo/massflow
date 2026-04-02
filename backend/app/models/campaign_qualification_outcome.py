"""
Snapshot de qualificação concluída por lead/campanha — para analytics e integrações (ex.: N8N).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class CampaignQualificationOutcome(Base):
    """
    Uma linha por sessão de qualificação concluída (session_id único).
    Duplica o payload enviado ao webhook final + answers em JSONB.
    """

    __tablename__ = "campaign_qualification_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(
        Integer,
        ForeignKey("campaign_qualification_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    campaign_name = Column(String(255), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_phone = Column(String(30), nullable=False, index=True)
    lead_name = Column(String(255), nullable=True)

    score_total = Column(Integer, nullable=False, default=0)
    classification = Column(String(60), nullable=True)
    notify_lawyer = Column(Boolean, nullable=False, default=True)

    answers_json = Column(JSONB, nullable=False, default=list)
    payload_json = Column(JSONB, nullable=False, default=dict)

    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
