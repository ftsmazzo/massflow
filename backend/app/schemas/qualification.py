"""
Schemas da qualificação por campanha.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QualificationConfigBody(BaseModel):
    enabled: bool = True
    questions_json: list[dict[str, Any]] = Field(default_factory=list)
    scoring_rules_json: dict[str, Any] = Field(default_factory=dict)
    classification_rules_json: dict[str, Any] = Field(default_factory=dict)
    final_webhook_url: str | None = None
    notify_lawyer: bool = True
    version: int = 1
    # Reconciliação a partir do histórico SaaS (Postgres chatMessages)
    reconcile_from_saas_chat: bool = False
    saas_tenant_id: int | None = None
    reconcile_notify_phone: str | None = None
    reconcile_notify_instance_id: int | None = None


class QualificationConfigResponse(QualificationConfigBody):
    tenant_id: int
    campaign_id: int
    updated_at: datetime | None = None


class QualificationAnswerIn(BaseModel):
    tenant_id: int
    campaign_id: int
    lead_phone: str = Field(..., min_length=3, max_length=40)
    lead_id: int | None = None
    lead_name: str | None = None
    step_key: str = Field(..., min_length=1, max_length=20)
    answer: str = Field(..., min_length=1, max_length=2000)
    question_text: str | None = None
    answer_meta: dict[str, Any] = Field(default_factory=dict)
    send_final_webhook: bool = True


class QualificationAnswerItem(BaseModel):
    step_key: str
    question_text: str | None = None
    answer_raw: str
    normalized_answer: str | None = None
    score_delta: int
    created_at: datetime | None = None


class QualificationSessionState(BaseModel):
    session_id: int
    status: str
    current_step: str | None = None
    next_step: str | None = None
    score_total: int
    classification: str | None = None
    completed: bool
    answers: list[QualificationAnswerItem] = Field(default_factory=list)
    webhook_sent: bool = False
    webhook_url: str | None = None
    confirmation_message: str | None = None
    recorded_step: str | None = None
    final_result: dict[str, Any] | None = None


class QualificationSessionQueryOut(BaseModel):
    found: bool
    state: QualificationSessionState | None = None


class QualificationSessionListItem(BaseModel):
    session_id: int
    lead_id: int | None = None
    lead_name: str | None = None
    lead_phone: str
    status: str
    score_total: int
    classification: str | None = None
    answers_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None


class QualificationSessionListOut(BaseModel):
    campaign_id: int
    total: int
    sessions: list[QualificationSessionListItem] = Field(default_factory=list)
