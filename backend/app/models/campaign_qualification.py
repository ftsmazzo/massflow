"""
Persistência de qualificação de leads por campanha (sessão + respostas + pontuação).
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class CampaignQualificationConfig(Base):
    __tablename__ = "campaign_qualification_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    enabled = Column(Boolean, default=True, nullable=False)
    questions_json = Column(JSONB, nullable=False, default=list)
    scoring_rules_json = Column(JSONB, nullable=False, default=dict)
    classification_rules_json = Column(JSONB, nullable=False, default=dict)
    final_webhook_url = Column(String(1000), nullable=True)
    notify_lawyer = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    # Reconciliação a partir do Postgres SaaS (ex.: tabela chatMessages)
    reconcile_from_saas_chat = Column(Boolean, default=False, nullable=False)
    saas_tenant_id = Column(Integer, nullable=True)
    reconcile_notify_phone = Column(String(30), nullable=True)
    reconcile_notify_instance_id = Column(
        Integer, ForeignKey("evolution_instances.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("tenant_id", "campaign_id", name="uq_qualification_config_tenant_campaign"),)


class CampaignQualificationSession(Base):
    __tablename__ = "campaign_qualification_sessions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    lead_phone = Column(String(30), nullable=False, index=True)
    lead_name = Column(String(255), nullable=True)

    status = Column(String(30), default="in_progress", nullable=False, index=True)  # in_progress | completed | abandoned
    current_step = Column(String(20), nullable=True)
    answers_count = Column(Integer, default=0, nullable=False)
    score_total = Column(Integer, default=0, nullable=False)
    classification = Column(String(60), nullable=True)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    notified_at = Column(DateTime, nullable=True)
    final_payload = Column(JSONB, nullable=False, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CampaignQualificationAnswer(Base):
    __tablename__ = "campaign_qualification_answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("campaign_qualification_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_key = Column(String(20), nullable=False, index=True)
    question_text = Column(Text, nullable=True)
    answer_raw = Column(Text, nullable=False)
    normalized_answer = Column(String(255), nullable=True)
    score_delta = Column(Integer, default=0, nullable=False)
    answer_meta = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
