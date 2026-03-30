"""
Reconcilia respostas da pré-triagem a partir do histórico SaaS (chatMessages) e grava no MassFlow.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.campaign_qualification import (
    CampaignQualificationAnswer,
    CampaignQualificationConfig,
    CampaignQualificationSession,
)
from app.models.evolution_instance import EvolutionInstance
from app.models.lead import Lead
from app.schemas.qualification import QualificationAnswerIn, QualificationSessionState
from app.services import qualification_service as qs
from app.services.evolution import send_text_sync
from app.services.saas_chat_messages import SaaSChatRow, fetch_chat_messages_for_phone

logger = logging.getLogger("massflow.reconcile")


def _try_reconcile_whatsapp_notify(
    db: Session,
    cfg: CampaignQualificationConfig,
    tenant_id: int,
    campaign_id: int,
    phone: str,
    lead: Lead | None,
    lead_name: str | None,
    last_state: QualificationSessionState | None,
) -> bool:
    """Envia resumo da qualificação via Evolution quando a sessão está completa e a config permite."""
    if not last_state or not last_state.completed:
        return False

    notify_raw = (getattr(cfg, "reconcile_notify_phone", None) or "").strip()
    notify_phone_digits = qs.normalize_phone(notify_raw) if notify_raw else ""
    inst_id = getattr(cfg, "reconcile_notify_instance_id", None)
    if inst_id and not notify_phone_digits:
        notify_phone_digits = phone
        logger.info(
            "reconcile_notify_phone vazio; enviando resumo para o telefone do lead (últimos dígitos …%s)",
            phone[-4:] if len(phone) >= 4 else phone,
        )
    if not inst_id:
        logger.warning(
            "reconcile_notify: sessão completa mas reconcile_notify_instance_id não configurado (campanha %s)",
            campaign_id,
        )
        return False
    if not notify_phone_digits:
        return False

    ev = (
        db.query(EvolutionInstance)
        .filter(
            EvolutionInstance.id == inst_id,
            EvolutionInstance.tenant_id == tenant_id,
        )
        .first()
    )
    if not ev:
        logger.warning(
            "reconcile_notify: instância id=%s não encontrada para tenant %s",
            inst_id,
            tenant_id,
        )
        return False

    summary = _build_notify_summary(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        phone=phone,
        lead_name=lead_name or (lead.name if lead else None),
        classification=last_state.classification,
        score=last_state.score_total,
        answers=last_state.answers,
    )
    try:
        send_text_sync(ev.api_url, ev.api_key or "", ev.name, notify_phone_digits, summary)
        logger.info(
            "reconcile_notify: WhatsApp enviado via instância %s para …%s",
            inst_id,
            notify_phone_digits[-4:] if len(notify_phone_digits) >= 4 else notify_phone_digits,
        )
        return True
    except Exception:
        logger.exception(
            "reconcile_notify: falha ao enviar WhatsApp (instância %s, destino …%s)",
            inst_id,
            notify_phone_digits[-4:] if len(notify_phone_digits) >= 4 else notify_phone_digits,
        )
        return False


def normalize_answer_step_e(raw: str) -> str:
    """Mapeia confirmações coloquiais para regras de score (sim/não)."""
    t = qs.norm_text(raw)
    if not t:
        return raw.strip()
    if any(x in t for x in ("sim", "claro", "pode", "ok", "com certeza", "quero", "desejo")):
        return "sim"
    if any(x in t for x in ("nao", "não", "negativo", "agora nao")):
        return "não"
    return raw.strip()


def slice_rows_for_latest_qualification_session(
    rows: list[SaaSChatRow],
    cfg: CampaignQualificationConfig,
) -> list[SaaSChatRow]:
    """
    Se o histórico tiver várias conversas no mesmo telefone, usa o trecho que começa na
    última ocorrência da primeira pergunta da campanha (texto em questions_json[0]).
    """
    if not rows:
        return rows
    q = cfg.questions_json if isinstance(cfg.questions_json, list) else []
    hint = ""
    if q and isinstance(q[0], dict):
        hint = str(q[0].get("text") or "").strip().lower()
    if not hint:
        hint = "dívida"
    # Última linha onde o assistente parece iniciar a triagem atual
    start = 0
    hint_short = hint[:24] if len(hint) > 24 else hint
    for i, r in enumerate(rows):
        c = (r.bot_content or "").lower()
        if hint_short and hint_short in c:
            start = i
        elif "quais" in c and "dívida" in c:
            start = i
    return rows[start:]


def extract_step_answers(rows: list[SaaSChatRow], steps: list[str]) -> dict[str, tuple[str, str]]:
    """
    Para cada step_key na ordem, obtém (question_text, answer) a partir do padrão chatMessages:
    resposta do passo i está em rows[i+1].userMessage; pergunta em rows[i].bot_content.
    """
    out: dict[str, tuple[str, str]] = {}
    n = len(steps)
    for i in range(n):
        if i + 1 >= len(rows):
            break
        qrow = rows[i]
        arow = rows[i + 1]
        step_key = steps[i]
        qtext = (qrow.bot_content or "").strip() or None
        ans = (arow.user_message or "").strip()
        if not ans:
            continue
        if step_key == "E":
            ans = normalize_answer_step_e(ans)
        out[step_key] = (qtext or f"Etapa {step_key}", ans)
    return out


def reconcile_lead_from_saas_chat(
    db: Session,
    tenant_id: int,
    campaign_id: int,
    lead_phone: str,
    lead_id: int | None = None,
    lead_name: str | None = None,
) -> dict[str, Any]:
    """
    Busca mensagens no SaaS, grava etapas faltantes e opcionalmente notifica WhatsApp.
    """
    phone = qs.normalize_phone(lead_phone)
    if not phone:
        raise ValueError("lead_phone inválido.")

    cfg = qs.ensure_config(db, tenant_id, campaign_id)
    if not getattr(cfg, "reconcile_from_saas_chat", False):
        raise ValueError("Reconciliação SaaS não está habilitada na config desta campanha.")

    steps = qs.ordered_steps(cfg)

    session = (
        db.query(CampaignQualificationSession)
        .filter(
            CampaignQualificationSession.tenant_id == tenant_id,
            CampaignQualificationSession.campaign_id == campaign_id,
            CampaignQualificationSession.lead_phone == phone,
        )
        .order_by(desc(CampaignQualificationSession.id))
        .first()
    )
    if session and session.status == "completed":
        lead_done = None
        if lead_id is not None:
            lead_done = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        if not lead_done:
            lead_done = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.phone == phone).first()
        last_done = qs.build_session_state_for_session(db, tenant_id, campaign_id, session)
        notification_done = _try_reconcile_whatsapp_notify(
            db, cfg, tenant_id, campaign_id, phone, lead_done, lead_name, last_done,
        )
        return {
            "ok": True,
            "skipped": True,
            "message": "Sessão já concluída; nada a reconciliar.",
            "session_id": session.id,
            "classification": session.classification,
            "steps_applied": [],
            "notification_sent": notification_done,
        }

    saas_tid = getattr(cfg, "saas_tenant_id", None)
    rows = fetch_chat_messages_for_phone(phone, saas_tenant_id=saas_tid)
    if not rows:
        raise ValueError("Nenhuma mensagem encontrada no histórico SaaS para este telefone.")

    raw_rows = rows
    rows = slice_rows_for_latest_qualification_session(rows, cfg)
    extracted = extract_step_answers(rows, steps)
    if not extracted:
        extracted = extract_step_answers(raw_rows, steps)
    if not extracted:
        raise ValueError(
            "Não foi possível extrair respostas alinhadas às etapas (histórico curto ou formato inesperado)."
        )

    existing_keys: set[str] = set()
    if session:
        existing_keys = {
            qs.normalize_step_key(r[0])
            for r in db.query(CampaignQualificationAnswer.step_key)
            .filter(CampaignQualificationAnswer.session_id == session.id)
            .all()
        }

    lead = None
    if lead_id is not None:
        lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        lead = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.phone == phone).first()

    steps_applied: list[str] = []
    last_state = None

    for step_key in steps:
        if step_key not in extracted:
            continue
        if step_key in existing_keys:
            continue
        qtext, ans = extracted[step_key]
        body = QualificationAnswerIn(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            lead_phone=phone,
            lead_id=lead.id if lead else None,
            lead_name=lead_name or (lead.name if lead else None),
            step_key=step_key,
            answer=ans,
            question_text=qtext,
            send_final_webhook=True,
        )
        last_state = qs.apply_qualification_answer(db, body)
        steps_applied.append(step_key)
        existing_keys.add(step_key)

    # Sessão pode ter ficado completa no loop, ou já estava completa (nenhuma etapa nova no loop).
    session = (
        db.query(CampaignQualificationSession)
        .filter(
            CampaignQualificationSession.tenant_id == tenant_id,
            CampaignQualificationSession.campaign_id == campaign_id,
            CampaignQualificationSession.lead_phone == phone,
        )
        .order_by(desc(CampaignQualificationSession.id))
        .first()
    )
    if session and session.status == "completed" and last_state is None:
        last_state = qs.build_session_state_for_session(db, tenant_id, campaign_id, session)

    notification_sent = _try_reconcile_whatsapp_notify(
        db, cfg, tenant_id, campaign_id, phone, lead, lead_name, last_state,
    )

    msg = (
        f"Reconciliação aplicada: {', '.join(steps_applied)}."
        if steps_applied
        else "Nenhuma etapa nova aplicada (já gravadas ou dados insuficientes)."
    )
    return {
        "ok": True,
        "skipped": False,
        "message": msg,
        "session_id": last_state.session_id if last_state else (session.id if session else None),
        "classification": last_state.classification if last_state else None,
        "steps_applied": steps_applied,
        "notification_sent": notification_sent,
    }


def _build_notify_summary(
    tenant_id: int,
    campaign_id: int,
    phone: str,
    lead_name: str | None,
    classification: str | None,
    score: int,
    answers: list[Any],
) -> str:
    lines = [
        "📋 Qualificação (reconciliação SaaS)",
        f"Tenant: {tenant_id} | Campanha: {campaign_id}",
        f"Lead: {lead_name or '-'} | Tel: {phone}",
        f"Classificação: {classification or '-'} | Pontos: {score}",
        "",
        "Respostas:",
    ]
    for a in answers:
        lines.append(f"- {a.step_key}: {a.answer_raw}")
    lines.append("")
    lines.append("MassFlow — resumo automático.")
    text = "\n".join(lines)
    if len(text) > 3500:
        return text[:3490] + "…"
    return text
