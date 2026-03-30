"""
Qualificação estruturada por campanha (A-E) com pontuação e webhook final.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
from app.models.user import User
from app.schemas.qualification import (
    QualificationAnswerIn,
    QualificationConfigBody,
    QualificationConfigResponse,
    QualificationSessionListItem,
    QualificationSessionListOut,
    QualificationSessionQueryOut,
    QualificationSessionState,
)
from app.services import qualification_service as qs
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
    campaign_id: int = Query(...),
    lead_phone: str = Query(...),
):
    _require_qualification_secret(request)
    phone = qs.normalize_phone(lead_phone)
    if not phone:
        raise HTTPException(status_code=422, detail="lead_phone inválido.")
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
    if not session:
        return QualificationSessionQueryOut(found=False, state=None)
    cfg = qs.ensure_config(db, tenant_id, campaign_id)
    steps = qs.ordered_steps(cfg)
    ans_steps = {
        a.step_key
        for a in db.query(CampaignQualificationAnswer.step_key).filter(
            CampaignQualificationAnswer.session_id == session.id
        ).all()
    }
    next_step = next((s for s in steps if s not in ans_steps), None)
    return QualificationSessionQueryOut(
        found=True,
        state=qs.build_session_state(db, session, next_step, cfg.final_webhook_url),
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


@router.post("/answer", response_model=QualificationSessionState)
def post_qualification_answer(
    body: QualificationAnswerIn,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    _require_qualification_secret(request)
    try:
        return qs.apply_qualification_answer(db, body)
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
):
    """
    Lê mensagens do Postgres SaaS (chatMessages), grava etapas faltantes e opcionalmente notifica WhatsApp.
    Requer `SAAS_CHAT_HISTORY_DATABASE_URL` e campanha com reconciliação habilitada.
    """
    _require_qualification_secret(request)
    if not (settings.SAAS_CHAT_HISTORY_DATABASE_URL or "").strip():
        raise HTTPException(
            status_code=503,
            detail="SAAS_CHAT_HISTORY_DATABASE_URL não configurada no backend.",
        )
    try:
        return reconcile_lead_from_saas_chat(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            lead_phone=lead_phone,
            lead_id=lead_id,
            lead_name=lead_name,
        )
    except ValueError as e:
        raise _map_qualification_value_error(e) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
