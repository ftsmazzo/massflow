"""
Lógica de qualificação por campanha (sessão, respostas, webhook final).
Usado pelo router HTTP e pela reconciliação SaaS.
"""
from __future__ import annotations

from datetime import datetime
import unicodedata
from typing import Any

import httpx
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.models.campaign import Campaign
from app.models.campaign_qualification import (
    CampaignQualificationAnswer,
    CampaignQualificationConfig,
    CampaignQualificationSession,
)
from app.models.lead import Lead
from app.schemas.qualification import (
    QualificationAnswerIn,
    QualificationAnswerItem,
    QualificationSessionState,
)


def normalize_phone(v: str) -> str:
    return "".join(c for c in str(v or "") if c.isdigit())


def norm_text(v: str) -> str:
    s = (v or "").strip().lower()
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def default_questions() -> list[dict[str, Any]]:
    return [
        {"key": "A", "text": "Tipos de dívida que mais pesam hoje"},
        {"key": "B", "text": "Valor aproximado total pago por mês com dívidas"},
        {"key": "C", "text": "Renda líquida aproximada"},
        {"key": "D", "text": "Depois dos essenciais, sobra para parcelas?"},
        {"key": "E", "text": "Deseja que a equipe avalie e ofereça horário?"},
    ]


def default_scoring_rules() -> dict[str, dict[str, int]]:
    return {
        "A": {
            "cartao": 20,
            "emprestimo pessoal": 20,
            "loja": 10,
            "carne": 10,
            "financiamento": 15,
            "outras": 5,
        },
        "B": {
            "ate r$ 500": 5,
            "r$ 501-1.500": 12,
            "r$ 1.501-3.000": 20,
            "acima de r$ 3.000": 30,
            "prefiro nao dizer": 0,
        },
        "C": {
            "ate r$ 500": 25,
            "r$ 501-1.500": 20,
            "r$ 1.501-3.000": 10,
            "acima de r$ 3.000": 5,
            "prefiro nao dizer": 0,
        },
        "D": {
            "sobra": 0,
            "sobra muito pouco": 20,
            "nao sobra": 30,
            "nao sei": 10,
        },
        "E": {
            "sim": 20,
            "nao": 0,
        },
    }


def default_classification_rules() -> dict[str, int]:
    return {
        "agendar_min_score": 70,
        "contato_posterior_min_score": 40,
    }


def ensure_config(db: Session, tenant_id: int, campaign_id: int) -> CampaignQualificationConfig:
    cfg = (
        db.query(CampaignQualificationConfig)
        .filter(
            CampaignQualificationConfig.tenant_id == tenant_id,
            CampaignQualificationConfig.campaign_id == campaign_id,
        )
        .first()
    )
    if cfg:
        return cfg
    cfg = CampaignQualificationConfig(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        enabled=True,
        questions_json=default_questions(),
        scoring_rules_json=default_scoring_rules(),
        classification_rules_json=default_classification_rules(),
        final_webhook_url=None,
        notify_lawyer=True,
        version=1,
    )
    db.add(cfg)
    db.commit()
    db.refresh(cfg)
    return cfg


def ordered_steps(cfg: CampaignQualificationConfig) -> list[str]:
    q = cfg.questions_json if isinstance(cfg.questions_json, list) else []
    steps: list[str] = []
    for item in q:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip().upper()
        if key and key not in steps:
            steps.append(key)
    return steps or ["A", "B", "C", "D", "E"]


def classify_score(score: int, rules: dict[str, Any]) -> str:
    agendar = int((rules or {}).get("agendar_min_score", 70))
    posterior = int((rules or {}).get("contato_posterior_min_score", 40))
    if score >= agendar:
        return "agendar"
    if score >= posterior:
        return "contato_posterior"
    return "contato_posterior"


def score_answer(step_key: str, answer: str, scoring_rules: dict[str, Any]) -> tuple[int, str]:
    norm = norm_text(answer)
    rules = scoring_rules.get(step_key, {}) if isinstance(scoring_rules, dict) else {}
    if not isinstance(rules, dict):
        return 0, norm
    if norm in rules and isinstance(rules[norm], int):
        return int(rules[norm]), norm
    for k, v in rules.items():
        if not isinstance(k, str) or not isinstance(v, int):
            continue
        if norm_text(k) in norm:
            return int(v), norm
    return 0, norm


def build_session_state(
    db: Session,
    session: CampaignQualificationSession,
    next_step: str | None,
    webhook_url: str | None,
    confirmation_message: str | None = None,
    recorded_step: str | None = None,
    final_result: dict[str, Any] | None = None,
) -> QualificationSessionState:
    ans_rows = (
        db.query(CampaignQualificationAnswer)
        .filter(CampaignQualificationAnswer.session_id == session.id)
        .order_by(CampaignQualificationAnswer.id.asc())
        .all()
    )
    answers = [
        QualificationAnswerItem(
            step_key=a.step_key,
            question_text=a.question_text,
            answer_raw=a.answer_raw,
            normalized_answer=a.normalized_answer,
            score_delta=a.score_delta,
            created_at=a.created_at,
        )
        for a in ans_rows
    ]
    return QualificationSessionState(
        session_id=session.id,
        status=session.status,
        current_step=session.current_step,
        next_step=next_step,
        score_total=session.score_total,
        classification=session.classification,
        completed=session.status == "completed",
        answers=answers,
        webhook_sent=session.notified_at is not None,
        webhook_url=webhook_url,
        confirmation_message=confirmation_message,
        recorded_step=recorded_step,
        final_result=final_result,
    )


def build_session_state_for_session(
    db: Session,
    tenant_id: int,
    campaign_id: int,
    session: CampaignQualificationSession,
) -> QualificationSessionState:
    """
    Monta QualificationSessionState a partir da sessão persistida (útil após reconciliação
    quando nenhuma etapa nova foi aplicada no loop mas a sessão já está completa).
    """
    cfg = ensure_config(db, tenant_id, campaign_id)
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        .first()
    )
    campaign_content = (campaign.content or {}) if campaign else {}
    steps = ordered_steps(cfg)
    ans_rows = (
        db.query(CampaignQualificationAnswer.step_key)
        .filter(CampaignQualificationAnswer.session_id == session.id)
        .all()
    )
    answered_steps = {k for (k,) in ans_rows}
    next_step = next((s for s in steps if s not in answered_steps), None)
    webhook_url = (
        cfg.final_webhook_url
        or str(campaign_content.get("campaign_webhook_url") or "").strip()
        or None
    )
    final_result = (
        {"classification": session.classification, "score_total": int(session.score_total or 0)}
        if session.status == "completed"
        else None
    )
    return build_session_state(
        db,
        session,
        next_step,
        webhook_url,
        confirmation_message=None,
        recorded_step=None,
        final_result=final_result,
    )


def _send_webhook_sync(webhook_url: str, payload: dict[str, Any]) -> bool:
    try:
        with httpx.Client(timeout=20.0, verify=settings.WEBHOOK_VERIFY_SSL) as client:
            resp = client.post(webhook_url, json=payload)
            resp.raise_for_status()
        return True
    except Exception:
        return False


def apply_qualification_answer(db: Session, body: QualificationAnswerIn) -> QualificationSessionState:
    """
    Grava uma etapa da qualificação (mesma regra do POST /api/qualification/answer).
    """
    phone = normalize_phone(body.lead_phone)
    if not phone:
        raise ValueError("lead_phone inválido.")

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == body.campaign_id, Campaign.tenant_id == body.tenant_id)
        .first()
    )
    if not campaign:
        raise ValueError("Campanha não encontrada para tenant informado.")
    cfg = ensure_config(db, body.tenant_id, body.campaign_id)
    if not cfg.enabled:
        raise ValueError("Qualificação está desativada nesta campanha.")

    step_key = body.step_key.strip().upper()
    steps = ordered_steps(cfg)
    if step_key not in steps:
        raise ValueError(f"step_key inválido. Use: {', '.join(steps)}")

    lead = None
    if body.lead_id is not None:
        lead = (
            db.query(Lead)
            .filter(Lead.id == body.lead_id, Lead.tenant_id == body.tenant_id)
            .first()
        )
    if not lead:
        lead = db.query(Lead).filter(Lead.tenant_id == body.tenant_id, Lead.phone == phone).first()

    session = (
        db.query(CampaignQualificationSession)
        .filter(
            CampaignQualificationSession.tenant_id == body.tenant_id,
            CampaignQualificationSession.campaign_id == body.campaign_id,
            CampaignQualificationSession.lead_phone == phone,
            CampaignQualificationSession.status == "in_progress",
        )
        .order_by(desc(CampaignQualificationSession.id))
        .first()
    )
    if not session:
        session = CampaignQualificationSession(
            tenant_id=body.tenant_id,
            campaign_id=body.campaign_id,
            lead_id=lead.id if lead else None,
            lead_phone=phone,
            lead_name=(body.lead_name or (lead.name if lead else None)),
            status="in_progress",
            current_step=steps[0] if steps else None,
            answers_count=0,
            score_total=0,
        )
        db.add(session)
        db.flush()

    score_delta, normalized = score_answer(step_key, body.answer, cfg.scoring_rules_json or {})
    existing = (
        db.query(CampaignQualificationAnswer)
        .filter(
            CampaignQualificationAnswer.session_id == session.id,
            CampaignQualificationAnswer.step_key == step_key,
        )
        .order_by(desc(CampaignQualificationAnswer.id))
        .first()
    )
    if existing:
        session.score_total = int(session.score_total or 0) - int(existing.score_delta or 0) + score_delta
        existing.answer_raw = body.answer
        existing.normalized_answer = normalized
        existing.score_delta = score_delta
        existing.question_text = body.question_text or existing.question_text
        existing.answer_meta = body.answer_meta or {}
    else:
        ans = CampaignQualificationAnswer(
            session_id=session.id,
            step_key=step_key,
            question_text=body.question_text,
            answer_raw=body.answer,
            normalized_answer=normalized,
            score_delta=score_delta,
            answer_meta=body.answer_meta or {},
        )
        db.add(ans)
        session.score_total = int(session.score_total or 0) + score_delta
        session.answers_count = int(session.answers_count or 0) + 1

    ans_rows = (
        db.query(CampaignQualificationAnswer.step_key)
        .filter(CampaignQualificationAnswer.session_id == session.id)
        .all()
    )
    answered_steps = {k for (k,) in ans_rows}
    next_step = next((s for s in steps if s not in answered_steps), None)
    session.current_step = next_step

    webhook_url = cfg.final_webhook_url or str((campaign.content or {}).get("campaign_webhook_url") or "").strip() or None
    if next_step is None:
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        session.classification = classify_score(int(session.score_total or 0), cfg.classification_rules_json or {})

    db.commit()
    db.refresh(session)

    if session.status == "completed":
        answers_data = (
            db.query(CampaignQualificationAnswer)
            .filter(CampaignQualificationAnswer.session_id == session.id)
            .order_by(CampaignQualificationAnswer.id.asc())
            .all()
        )
        payload = {
            "event": "campaign_qualification_completed",
            "tenant_id": session.tenant_id,
            "campaign_id": session.campaign_id,
            "campaign_name": campaign.name,
            "lead_id": session.lead_id,
            "lead_phone": session.lead_phone,
            "lead_name": session.lead_name,
            "session_id": session.id,
            "score_total": session.score_total,
            "classification": session.classification,
            "notify_lawyer": bool(cfg.notify_lawyer),
            "answers": [
                {
                    "step_key": a.step_key,
                    "question_text": a.question_text,
                    "answer_raw": a.answer_raw,
                    "normalized_answer": a.normalized_answer,
                    "score_delta": a.score_delta,
                }
                for a in answers_data
            ],
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            "source": "massflow",
        }
        session.final_payload = payload
        if body.send_final_webhook and webhook_url and session.notified_at is None:
            try:
                if _send_webhook_sync(webhook_url, payload):
                    session.notified_at = datetime.utcnow()
            except Exception:
                pass
        db.commit()

    db.refresh(session)
    final_result = (
        {"classification": session.classification, "score_total": int(session.score_total or 0)}
        if session.status == "completed"
        else None
    )
    msg = (
        f"Resposta da etapa {step_key} gravada com sucesso."
        if session.status != "completed"
        else "Qualificação concluída com sucesso."
    )
    return build_session_state(
        db,
        session,
        next_step,
        webhook_url,
        confirmation_message=msg,
        recorded_step=step_key,
        final_result=final_result,
    )
