"""
Qualificação estruturada por campanha (A-E) com pontuação e webhook final.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.campaign import Campaign
from app.models.campaign_qualification import (
    CampaignQualificationAnswer,
    CampaignQualificationSession,
)
from app.models.campaign_qualification_outcome import CampaignQualificationOutcome
from app.models.user import User
from app.schemas.qualification import (
    QualificationAnswerIn,
    QualificationCompletedPayloadIn,
    QualificationConfigBody,
    QualificationConfigResponse,
    QualificationOutcomeListItem,
    QualificationOutcomeListOut,
    QualificationSessionListItem,
    QualificationSessionListOut,
    QualificationSessionQueryOut,
    QualificationSessionState,
)
from app.services import qualification_service as qs
from app.services.campaign_resolution import resolve_campaign_id_for_qualification
from app.services.reconciliation_trigger import run_reconcile_safe
from app.services.saas_chat_messages import saas_database_configured
from app.services.saas_reconciliation import reconcile_lead_from_saas_chat

router = APIRouter(prefix="/qualification", tags=["Qualification"])


def _require_qualification_secret(request: Request) -> None:
    expected = (settings.QUALIFICATION_SECRET or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Endpoint desativado: defina QUALIFICATION_SECRET no backend.",
        )
    header_secret = (request.headers.get("X-Massflow-Qualification-Secret") or "").strip()
    auth = (request.headers.get("Authorization") or "").strip()
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if header_secret == expected or bearer == expected:
        return
    raise HTTPException(status_code=401, detail="Credencial inválida ou ausente.")


def _map_qualification_value_error(e: ValueError) -> HTTPException:
    msg = str(e)
    if "Campanha não encontrada" in msg:
        return HTTPException(status_code=404, detail=msg)
    return HTTPException(status_code=422, detail=msg)


@router.get("/campaigns/{campaign_id}/config", response_model=QualificationConfigResponse)
def get_campaign_qualification_config(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    cfg = qs.ensure_config(db, tenant_id, campaign_id)
    return QualificationConfigResponse(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        enabled=cfg.enabled,
        questions_json=cfg.questions_json or [],
        scoring_rules_json=cfg.scoring_rules_json or {},
        classification_rules_json=cfg.classification_rules_json or {},
        final_webhook_url=cfg.final_webhook_url,
        notify_lawyer=cfg.notify_lawyer,
        version=cfg.version,
        updated_at=cfg.updated_at,
        reconcile_from_saas_chat=bool(getattr(cfg, "reconcile_from_saas_chat", False)),
        saas_tenant_id=getattr(cfg, "saas_tenant_id", None),
        reconcile_notify_phone=getattr(cfg, "reconcile_notify_phone", None),
        reconcile_notify_instance_id=getattr(cfg, "reconcile_notify_instance_id", None),
    )


@router.put("/campaigns/{campaign_id}/config", response_model=QualificationConfigResponse)
def put_campaign_qualification_config(
    campaign_id: int,
    body: QualificationConfigBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    cfg = qs.ensure_config(db, tenant_id, campaign_id)
    cfg.enabled = body.enabled
    cfg.questions_json = body.questions_json or qs.default_questions()
    cfg.scoring_rules_json = body.scoring_rules_json or qs.default_scoring_rules()
    cfg.classification_rules_json = body.classification_rules_json or qs.default_classification_rules()
    cfg.final_webhook_url = (body.final_webhook_url or "").strip() or None
    cfg.notify_lawyer = body.notify_lawyer
    cfg.version = body.version
    cfg.reconcile_from_saas_chat = body.reconcile_from_saas_chat
    cfg.saas_tenant_id = body.saas_tenant_id
    cfg.reconcile_notify_phone = (body.reconcile_notify_phone or "").strip() or None
    cfg.reconcile_notify_instance_id = body.reconcile_notify_instance_id
    db.commit()
    db.refresh(cfg)
    return QualificationConfigResponse(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        enabled=cfg.enabled,
        questions_json=cfg.questions_json or [],
        scoring_rules_json=cfg.scoring_rules_json or {},
        classification_rules_json=cfg.classification_rules_json or {},
        final_webhook_url=cfg.final_webhook_url,
        notify_lawyer=cfg.notify_lawyer,
        version=cfg.version,
        updated_at=cfg.updated_at,
        reconcile_from_saas_chat=bool(cfg.reconcile_from_saas_chat),
        saas_tenant_id=cfg.saas_tenant_id,
        reconcile_notify_phone=cfg.reconcile_notify_phone,
        reconcile_notify_instance_id=cfg.reconcile_notify_instance_id,
    )


@router.get("/session-state", response_model=QualificationSessionQueryOut)
def get_session_state(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: int = Query(...),
    campaign_id: int | None = Query(
        None,
        description="Opcional: se omitido, resolve pelo último campaign_inbound_replies do lead.",
    ),
    lead_phone: str = Query(...),
):
    _require_qualification_secret(request)
    phone = qs.normalize_phone(lead_phone)
    if not phone:
        raise HTTPException(status_code=422, detail="lead_phone inválido.")

    cid = campaign_id
    if cid is None:
        cid = resolve_campaign_id_for_qualification(db, tenant_id, phone, None, None)
        if cid is None:
            return QualificationSessionQueryOut(found=False, state=None, campaign_id=None)

    session = (
        db.query(CampaignQualificationSession)
        .filter(
            CampaignQualificationSession.tenant_id == tenant_id,
            CampaignQualificationSession.campaign_id == cid,
            CampaignQualificationSession.lead_phone == phone,
        )
        .order_by(desc(CampaignQualificationSession.id))
        .first()
    )
    if not session:
        return QualificationSessionQueryOut(found=False, state=None, campaign_id=cid)
    cfg = qs.ensure_config(db, tenant_id, cid)
    steps = qs.ordered_steps(cfg)
    ans_steps = {
        qs.normalize_step_key(r[0])
        for r in db.query(CampaignQualificationAnswer.step_key).filter(
            CampaignQualificationAnswer.session_id == session.id
        ).all()
    }
    # GET é só leitura: não chama repair aqui (use POST /repair-session quando precisar fechar sessão).

    next_step = next((s for s in steps if s not in ans_steps), None)
    webhook_url = qs.effective_webhook_url_for_campaign(db, tenant_id, cid, cfg)
    final_result = (
        {"classification": session.classification, "score_total": int(session.score_total or 0)}
        if session.status == "completed"
        else None
    )
    return QualificationSessionQueryOut(
        found=True,
        state=qs.build_session_state(
            db, session, next_step, webhook_url, final_result=final_result
        ),
        campaign_id=cid,
    )


@router.get("/campaigns/{campaign_id}/sessions", response_model=QualificationSessionListOut)
def list_campaign_sessions(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(200, ge=1, le=1000),
):
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    rows = (
        db.query(CampaignQualificationSession)
        .filter(
            CampaignQualificationSession.tenant_id == tenant_id,
            CampaignQualificationSession.campaign_id == campaign_id,
        )
        .order_by(desc(CampaignQualificationSession.id))
        .limit(limit)
        .all()
    )
    out = [
        QualificationSessionListItem(
            session_id=s.id,
            lead_id=s.lead_id,
            lead_name=s.lead_name,
            lead_phone=s.lead_phone,
            status=s.status,
            score_total=int(s.score_total or 0),
            classification=s.classification,
            answers_count=int(s.answers_count or 0),
            started_at=s.started_at,
            completed_at=s.completed_at,
        )
        for s in rows
    ]
    return QualificationSessionListOut(campaign_id=campaign_id, total=len(out), sessions=out)


@router.get("/campaigns/{campaign_id}/outcomes", response_model=QualificationOutcomeListOut)
def list_campaign_qualification_outcomes(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(500, ge=1, le=2000),
):
    """
    Lista snapshots de qualificações concluídas gravados em `campaign_qualification_outcomes`
    (útil para relatórios e avaliação de campanha).
    """
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    rows = (
        db.query(CampaignQualificationOutcome)
        .filter(
            CampaignQualificationOutcome.tenant_id == tenant_id,
            CampaignQualificationOutcome.campaign_id == campaign_id,
        )
        .order_by(desc(CampaignQualificationOutcome.id))
        .limit(limit)
        .all()
    )
    out = [
        QualificationOutcomeListItem(
            id=r.id,
            session_id=r.session_id,
            lead_id=r.lead_id,
            lead_phone=r.lead_phone,
            lead_name=r.lead_name,
            score_total=int(r.score_total or 0),
            classification=r.classification,
            completed_at=r.completed_at,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return QualificationOutcomeListOut(campaign_id=campaign_id, total=len(out), outcomes=out)


@router.post("/record-completed-outcome")
def post_record_qualification_completed_outcome(
    body: QualificationCompletedPayloadIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Grava ou atualiza o snapshot da qualificação concluída (mesmo payload do webhook final).
    Use no N8N após o Webhook (ou em paralelo) com `X-Massflow-Qualification-Secret`.
    Idempotente por `session_id`.
    """
    _require_qualification_secret(request)

    campaign_id = body.campaign_id
    if campaign_id is None:
        sess = (
            db.query(CampaignQualificationSession)
            .filter(
                CampaignQualificationSession.id == body.session_id,
                CampaignQualificationSession.tenant_id == body.tenant_id,
            )
            .first()
        )
        if not sess:
            raise HTTPException(
                status_code=422,
                detail=(
                    "campaign_id ausente: inclua campaign_id no JSON ou use um session_id "
                    "de uma sessão de qualificação existente neste tenant."
                ),
            )
        campaign_id = sess.campaign_id

    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.tenant_id == body.tenant_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada para tenant informado.")

    payload: dict[str, Any] = dict(body.model_dump())
    payload["campaign_id"] = campaign_id
    if not str(payload.get("campaign_name") or "").strip():
        payload["campaign_name"] = campaign.name
    try:
        qs.upsert_qualification_outcome(db, payload)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise
    return {"ok": True, "session_id": body.session_id, "message": "Outcome gravado ou atualizado."}


@router.post("/answer", response_model=QualificationSessionState)
def post_qualification_answer(
    body: QualificationAnswerIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    _require_qualification_secret(request)
    try:
        state = qs.apply_qualification_answer(db, body)
    except ValueError as e:
        raise _map_qualification_value_error(e) from e
    cfg = qs.ensure_config(db, body.tenant_id, body.campaign_id)
    if (
        saas_database_configured()
        and bool(getattr(cfg, "reconcile_from_saas_chat", False))
        and not state.completed
    ):
        background_tasks.add_task(
            run_reconcile_safe,
            body.tenant_id,
            body.campaign_id,
            qs.normalize_phone(body.lead_phone),
            body.lead_id,
            body.lead_name,
            "after_answer",
        )
    return state


@router.post("/repair-session", response_model=QualificationSessionState)
def post_repair_qualification_session(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: int = Query(...),
    campaign_id: int = Query(...),
    lead_phone: str = Query(...),
    send_final_webhook: bool = Query(True),
):
    """
    Fecha sessão em `in_progress` quando já existem respostas para todas as etapas (A–E),
    mas classificação/webhook não rodaram (ex.: erro após o último POST /answer).
    Se faltar etapa no banco, retorna 422 com a lista (em geral falta `step_key` E).
    """
    _require_qualification_secret(request)
    try:
        return qs.repair_stale_qualification_session(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            lead_phone=lead_phone,
            send_final_webhook=send_final_webhook,
        )
    except ValueError as e:
        raise _map_qualification_value_error(e) from e


@router.post("/reconcile-from-saas")
def post_reconcile_from_saas(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: int = Query(...),
    campaign_id: int = Query(...),
    lead_phone: str = Query(...),
    lead_id: int | None = Query(None),
    lead_name: str | None = Query(None),
    send_whatsapp: bool = Query(
        True,
        description="Se false, aplica respostas e devolve classification_summary_text sem enviar WhatsApp.",
    ),
):
    """
    Lê mensagens do Postgres SaaS (chatMessages), grava etapas faltantes, devolve `classification_summary_text`
    (mesmo texto do resumo classificatório) e, com send_whatsapp=true, envia o WhatsApp de conclusão como no fluxo real.
    Requer Postgres SaaS (SAAS_PG_* ou SAAS_CHAT_HISTORY_DATABASE_URL) e campanha com reconciliação habilitada.
    """
    _require_qualification_secret(request)
    if not saas_database_configured():
        raise HTTPException(
            status_code=503,
            detail="Postgres SaaS não configurado: defina SAAS_PG_HOST, SAAS_PG_USER, SAAS_PG_DATABASE "
            "(e senha) ou SAAS_CHAT_HISTORY_DATABASE_URL.",
        )
    try:
        return reconcile_lead_from_saas_chat(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            lead_phone=lead_phone,
            lead_id=lead_id,
            lead_name=lead_name,
            send_whatsapp=send_whatsapp,
        )
    except ValueError as e:
        raise _map_qualification_value_error(e) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
