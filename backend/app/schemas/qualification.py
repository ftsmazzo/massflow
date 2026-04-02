"""
Schemas da qualificação por campanha.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    # Campanha usada na consulta (informada ou resolvida pelo último inbound).
    campaign_id: int | None = None


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


class QualificationCompletedPayloadIn(BaseModel):
    """
    Mesmo formato do webhook `campaign_qualification_completed` (corpo JSON).
    Campos extras são aceitos e vão para `payload_json` ao gravar.

    Tolera tipos vindos de N8N/replays: strings numéricas, `lead_phone` como número,
    `campaign_id` omitido (o backend resolve por `session_id` + `tenant_id`).
    """

    model_config = ConfigDict(extra="allow")

    event: str = "campaign_qualification_completed"
    tenant_id: int
    campaign_id: int | None = None
    campaign_name: str = ""
    lead_id: int | None = None
    lead_phone: str
    lead_name: str | None = None
    session_id: int
    score_total: int
    classification: str | None = None
    notify_lawyer: bool = True
    answers: list[dict[str, Any]] = Field(default_factory=list)
    completed_at: str | None = None
    source: str = "massflow"

    @field_validator("tenant_id", "session_id", "score_total", mode="before")
    @classmethod
    def _coerce_required_int(cls, v: Any) -> int:
        if v is None or v == "":
            raise ValueError("valor obrigatório")
        return int(v)

    @field_validator("lead_id", mode="before")
    @classmethod
    def _coerce_optional_int(cls, v: Any) -> int | None:
        if v is None or v == "":
            return None
        return int(v)

    @field_validator("campaign_id", mode="before")
    @classmethod
    def _coerce_optional_campaign_id(cls, v: Any) -> int | None:
        if v is None or v == "":
            return None
        return int(v)

    @field_validator("lead_phone", mode="before")
    @classmethod
    def _coerce_lead_phone_str(cls, v: Any) -> str:
        if v is None:
            raise ValueError("lead_phone obrigatório")
        return "".join(c for c in str(v) if c.isdigit()) or str(v).strip()

    @field_validator("notify_lawyer", mode="before")
    @classmethod
    def _coerce_bool(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if v in (None, "", 0, "0", "false", "False"):
            return False
        return True


class QualificationOutcomeListItem(BaseModel):
    id: int
    session_id: int
    lead_id: int | None = None
    lead_phone: str
    lead_name: str | None = None
    score_total: int
    classification: str | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class QualificationOutcomeListOut(BaseModel):
    campaign_id: int
    total: int
    outcomes: list[QualificationOutcomeListItem] = Field(default_factory=list)
