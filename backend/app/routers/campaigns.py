"""
Campanhas: CRUD, criação, upload de mídia (arquivo anexado) e disparo em background.
"""
import asyncio
import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.campaign_inbound_reply import CampaignInboundReply
from app.models.evolution_instance import EvolutionInstance
from app.models.lead import Lead
from app.models.list import List
from app.models.tag import Tag
from app.schemas.campaign import (
    CampaignBulkDelete,
    CampaignCreate,
    CampaignInboundReplyItem,
    CampaignReportMessageItem,
    CampaignReportReplyItem,
    CampaignReportResponse,
    CampaignReportSummary,
    CampaignResponse,
    CampaignTagFailedContactsBody,
    CampaignTagFailedContactsResponse,
    CampaignUpdate,
)
from app.services.campaign_sender import _resolve_text, run_campaign_sync
from app.services.inbound_evolution import (
    extract_evolution_instance_name,
    extract_inbound_text_and_phone,
    normalize_inbound_payload,
    normalize_phone_digits,
    phones_match_for_lead,
)

# Pasta de uploads: backend/uploads (criada ao subir; em Docker use volume se quiser persistir)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = BACKEND_ROOT / "uploads"
ALLOWED_MEDIA = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "video/mp4", "video/3gpp", "audio/ogg", "audio/mpeg", "audio/mp4", "audio/webm",
    "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
EXT_FROM_MIME = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp",
    "video/mp4": ".mp4", "video/3gpp": ".3gp",
    "audio/ogg": ".ogg", "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/webm": ".weba",
    "application/pdf": ".pdf", "application/msword": ".doc", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
logger = logging.getLogger(__name__)

# Exclusão: rascunho, cancelada, concluída ou agendada (ainda não disparada). Em andamento: não excluir.
DELETABLE_CAMPAIGN_STATUSES = frozenset({"draft", "cancelled", "completed", "scheduled"})


def _fold_accents(s: str) -> str:
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _extract_keywords(content: dict) -> list[str]:
    raw = content.get("response_keywords")
    if isinstance(raw, list):
        return [str(k).strip().lower() for k in raw if str(k).strip()]
    if isinstance(raw, str):
        return [k.strip().lower() for k in raw.split(",") if k.strip()]
    return []


def _matched_keyword_list(text: str, keywords: list[str]) -> list[str]:
    txt = _fold_accents((text or "").strip().lower())
    out: list[str] = []
    for k in keywords:
        if _fold_accents(k) in txt and k not in out:
            out.append(k)
    return out


def _n8n_webhook_url(content: dict) -> str:
    return str(
        content.get("campaign_webhook_url")
        or content.get("response_webhook_url")
        or settings.DEFAULT_CAMPAIGN_WEBHOOK_URL
        or ""
    ).strip()


def _with_default_campaign_webhook(content: dict | None) -> dict:
    out = dict(content or {})
    if not str(out.get("campaign_webhook_url") or "").strip():
        out["campaign_webhook_url"] = settings.DEFAULT_CAMPAIGN_WEBHOOK_URL
    return out


def _dt_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _resolved_campaign_outbound_text(content: dict, lead: Lead) -> tuple[str, str]:
    """
    Texto/caption efetivamente enviado ao lead no disparo (mesma lógica do campaign_sender),
    com {nome}, {telefone}, {email} substituídos.
    """
    c = content if isinstance(content, dict) else {}
    content_type = (c.get("type") or "text").lower()
    text_template = c.get("text") or c.get("caption") or ""
    caption_template = str(c.get("caption") or c.get("text") or "")
    if content_type == "text":
        body = _resolve_text(str(text_template), lead)
    else:
        body = _resolve_text(caption_template, lead)
    return content_type, body


def _resolve_sent_campaign_for_reply(
    db: Session,
    tenant_id: int,
    lead_id: int,
    evolution_instance_id: int | None,
) -> tuple[CampaignMessage | None, Campaign | None]:
    """
    Último disparo enviado ao lead. Com evolution_instance_id (número que recebeu a resposta
    no webhook Evolution), restringe ao mesmo envio — necessário com várias instâncias.
    """
    base = (
        db.query(CampaignMessage, Campaign)
        .join(Campaign, Campaign.id == CampaignMessage.campaign_id)
        .filter(
            Campaign.tenant_id == tenant_id,
            CampaignMessage.lead_id == lead_id,
            CampaignMessage.status == "sent",
        )
    )
    if evolution_instance_id is not None:
        row = (
            base.filter(CampaignMessage.evolution_instance_id == evolution_instance_id)
            .order_by(desc(CampaignMessage.sent_at), desc(CampaignMessage.id))
            .first()
        )
        if row:
            return row[0], row[1]
        logger.warning(
            "campaign_inbound sem CampaignMessage sent para lead_id=%s evolution_instance_id=%s; "
            "usando ultimo envio em qualquer instancia",
            lead_id,
            evolution_instance_id,
        )
    row = (
        base.order_by(desc(CampaignMessage.sent_at), desc(CampaignMessage.id))
        .first()
    )
    if not row:
        return None, None
    return row[0], row[1]


@router.get("", response_model=list[CampaignResponse])
def list_campaigns(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: str | None = None,
):
    """Lista campanhas do tenant."""
    tenant_id = user.tenant_id
    q = db.query(Campaign).filter(Campaign.tenant_id == tenant_id)
    if status:
        q = q.filter(Campaign.status == status)
    campaigns = q.order_by(Campaign.created_at.desc()).all()
    return campaigns


async def _inbound_campaign_reply_impl(
    tenant_id: int,
    request: Request,
    db: Session,
    debug: bool,
):
    """
    Evolution envia aqui as mensagens recebidas do lead (campo `instance` = nome da instância na API).
    O disparo atribuído é o último envio **para aquele lead na mesma instância** (vários números = várias instâncias).
    Com URL de webhook: após checar palavras-chave (se configuradas), POST ao n8n.

    Rotas: POST /inbound/{tenant_id} e .../messages-upsert (webhook_by_events).
    """
    peer = request.client.host if request.client else "?"
    logger.info(
        "campaign_inbound_hit tenant_id=%s path=%s client=%s",
        tenant_id,
        request.url.path,
        peer,
    )
    try:
        payload_raw = await request.json()
    except Exception:
        logger.warning("campaign_inbound tenant_id=%s json_invalid client=%s", tenant_id, peer)
        raise HTTPException(status_code=400, detail="Payload JSON inválido.")
    norm = normalize_inbound_payload(payload_raw)
    if not norm:
        raise HTTPException(
            status_code=400,
            detail="Payload inválido: envie um objeto JSON ou lista com um objeto (webhook Evolution).",
        )

    logger.info(
        "campaign_inbound_received tenant_id=%s event=%s keys=%s",
        tenant_id,
        norm.get("event"),
        list(norm.keys())[:25],
    )

    extracted = extract_inbound_text_and_phone(payload_raw)
    if not extracted:
        logger.info(
            "campaign_inbound tenant_id=%s reason=sem_texto_ou_telefone event=%s",
            tenant_id,
            norm.get("event"),
        )
        out: dict = {"matched": False, "forwarded": False, "reason": "sem_texto_ou_telefone"}
        if debug:
            out["debug"] = {
                "event": norm.get("event"),
                "top_level_keys": list(norm.keys()),
                "hint": "Evolution: POST nesta URL com evento messages.upsert. JSON no formato padrão da Evolution API.",
            }
        return out

    inbound_text, inbound_phone = extracted

    ev_instance_name = extract_evolution_instance_name(payload_raw)
    evolution_instance_row: EvolutionInstance | None = None
    if ev_instance_name:
        evolution_instance_row = (
            db.query(EvolutionInstance)
            .filter(
                EvolutionInstance.tenant_id == tenant_id,
                func.lower(EvolutionInstance.name) == ev_instance_name.lower(),
            )
            .first()
        )
        if not evolution_instance_row:
            logger.warning(
                "campaign_inbound instancia Evolution nao cadastrada no tenant: name=%s tenant_id=%s",
                ev_instance_name,
                tenant_id,
            )

    ev_instance_id: int | None = evolution_instance_row.id if evolution_instance_row else None

    tenant_leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    lead = next((l for l in tenant_leads if phones_match_for_lead(inbound_phone, l.phone)), None)
    if not lead:
        logger.info(
            "campaign_inbound tenant_id=%s reason=lead_nao_encontrado",
            tenant_id,
        )
        out = {"matched": False, "forwarded": False, "reason": "lead_nao_encontrado"}
        if debug:
            out["debug"] = {
                "inbound_phone_normalized": inbound_phone,
                "sample_lead_phones": [normalize_phone_digits(l.phone) for l in tenant_leads[:5]],
            }
        return out
    lead.last_response_at = datetime.utcnow()
    db.commit()

    latest_msg, campaign = _resolve_sent_campaign_for_reply(db, tenant_id, lead.id, ev_instance_id)
    if not latest_msg or not campaign:
        logger.info(
            "campaign_inbound tenant_id=%s reason=sem_disparo_previo lead_id=%s ev_instance_id=%s",
            tenant_id,
            lead.id,
            ev_instance_id,
        )
        return {"stored": False, "matched": False, "forwarded": False, "reason": "sem_disparo_previo"}

    logger.info(
        "campaign_inbound atribuido tenant_id=%s campaign_id=%s lead_id=%s evolution_instance_id=%s ev_instance_name=%s",
        tenant_id,
        campaign.id,
        lead.id,
        ev_instance_id,
        ev_instance_name,
    )

    content = campaign.content or {}
    webhook_url = _n8n_webhook_url(content)
    keywords = _extract_keywords(content)
    matched_kw = _matched_keyword_list(inbound_text, keywords) if keywords else []
    if not webhook_url:
        forward_n8n = False
        skip_reason = "sem_webhook"
    elif keywords and not matched_kw:
        forward_n8n = False
        skip_reason = "keyword_sem_match"
    else:
        forward_n8n = True
        skip_reason = None

    lead_display_name = (lead.name or "").strip() or "Contato"
    reply_row = CampaignInboundReply(
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        lead_id=lead.id,
        evolution_instance_id=ev_instance_id,
        message_text=inbound_text,
        forwarded_to_webhook=False,
        webhook_skip_reason=skip_reason if not forward_n8n else None,
    )
    db.add(reply_row)
    db.flush()

    received_at = datetime.utcnow()
    outbound_type, outbound_text = _resolved_campaign_outbound_text(content, lead)

    outbound_payload = {
        "event": "campaign_reply_received",
        "tenant_id": tenant_id,
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "campaign_outbound_type": outbound_type,
        "campaign_outbound_message": outbound_text,
        "lead_id": lead.id,
        "lead_name": lead_display_name,
        "lead_phone": lead.phone,
        "lead_email": lead.email,
        "lead_message": inbound_text,
        "matched_keywords": matched_kw,
        "inbound_reply_id": reply_row.id,
        "received_at": _dt_iso(received_at),
        "campaign_message_sent_at": _dt_iso(latest_msg.sent_at),
        "lead_created_at": _dt_iso(lead.created_at),
        "lead_last_sent_at": _dt_iso(lead.last_sent_at),
        "lead_last_response_at": _dt_iso(lead.last_response_at),
        "source": "massflow",
        "evolution_instance_name": ev_instance_name,
        "evolution_instance_id": ev_instance_id,
    }

    if not forward_n8n:
        db.commit()
        logger.info(
            "campaign_inbound armazenado tenant_id=%s campaign_id=%s lead_id=%s reply_id=%s skip=%s",
            tenant_id,
            campaign.id,
            lead.id,
            reply_row.id,
            skip_reason,
        )
        return {
            "stored": True,
            "matched": True,
            "forwarded": False,
            "reason": skip_reason,
            "matched_keywords": matched_kw,
            "inbound_reply_id": reply_row.id,
        }

    try:
        async with httpx.AsyncClient(timeout=20.0, verify=settings.WEBHOOK_VERIFY_SSL) as client:
            resp = await client.post(webhook_url, json=outbound_payload)
            resp.raise_for_status()
        reply_row.forwarded_to_webhook = True
        reply_row.webhook_skip_reason = None
        db.commit()
        logger.info(
            "campaign_inbound webhook_ok tenant_id=%s campaign_id=%s lead_id=%s reply_id=%s http=%s",
            tenant_id,
            campaign.id,
            lead.id,
            reply_row.id,
            resp.status_code,
        )
    except Exception as e:
        logger.exception(
            "campaign_inbound webhook_falhou tenant_id=%s campaign_id=%s lead_id=%s",
            tenant_id,
            campaign.id,
            lead.id,
        )
        reply_row.webhook_skip_reason = "erro_ao_enviar_webhook"
        db.commit()
        return {
            "stored": True,
            "matched": True,
            "forwarded": False,
            "reason": "erro_ao_enviar_webhook",
            "error": str(e)[:500],
            "matched_keywords": matched_kw,
            "inbound_reply_id": reply_row.id,
        }

    return {
        "stored": True,
        "matched": True,
        "forwarded": True,
        "matched_keywords": matched_kw,
        "inbound_reply_id": reply_row.id,
    }


@router.get("/inbound/{tenant_id}/ping")
def inbound_webhook_ping(tenant_id: int):
    """
    Público (sem JWT): use no navegador ou `curl` para provar que a URL pública do backend
    alcança este path — o mesmo host/path base que a Evolution deve usar no POST.
    """
    return {"ok": True, "tenant_id": tenant_id, "path": f"/api/campaigns/inbound/{tenant_id}"}


@router.post("/inbound/{tenant_id}")
@router.post("/inbound/{tenant_id}/messages-upsert")
@router.post("/inbound/{tenant_id}/messages.upsert")
async def inbound_campaign_reply(
    tenant_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    debug: bool = Query(False, description="Inclui dados de diagnóstico na resposta"),
):
    return await _inbound_campaign_reply_impl(tenant_id, request, db, debug)


@router.get("/inbound-config")
def get_inbound_webhook_config(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
):
    """
    URL do webhook que a Evolution deve chamar ao receber mensagem do lead.
    A URL absoluta vem do próprio pedido (host/scheme); atrás de proxy use headers corretos (ex.: --proxy-headers no uvicorn).
    """
    tenant_id = user.tenant_id
    path = f"/api/campaigns/inbound/{tenant_id}"
    base = str(request.base_url).rstrip("/")
    full_url = f"{base}{path}"
    # Evolution com webhook_by_events=true envia para URL + /messages-upsert (ambas as rotas são aceitas)
    url_messages_upsert = f"{full_url}/messages-upsert"
    return {
        "tenant_id": tenant_id,
        "inbound_webhook_path": path,
        "inbound_webhook_url": full_url,
        "inbound_webhook_url_messages_upsert": url_messages_upsert,
        "hint": "Na Evolution: evento MESSAGES_UPSERT. Se webhook_by_events estiver ativo, use inbound_webhook_url_messages_upsert ou a base inbound_webhook_url (ambas funcionam).",
    }


@router.get("/inbound-replies", response_model=list[CampaignInboundReplyItem])
def list_inbound_replies(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
):
    """Últimas respostas de leads recebidas (persistidas no MassFlow, com ou sem n8n)."""
    tenant_id = user.tenant_id
    rows = (
        db.query(
            CampaignInboundReply,
            Campaign.name,
            Lead.name,
            Lead.phone,
            EvolutionInstance.display_name,
            EvolutionInstance.name,
        )
        .join(Campaign, Campaign.id == CampaignInboundReply.campaign_id)
        .join(Lead, Lead.id == CampaignInboundReply.lead_id)
        .outerjoin(EvolutionInstance, EvolutionInstance.id == CampaignInboundReply.evolution_instance_id)
        .filter(CampaignInboundReply.tenant_id == tenant_id)
        .order_by(desc(CampaignInboundReply.created_at))
        .limit(limit)
        .all()
    )
    out: list[CampaignInboundReplyItem] = []
    for r, campaign_name, lead_name, lead_phone, inst_display, inst_name in rows:
        inst_label = ((inst_display or "").strip() or (inst_name or "").strip() or None)
        out.append(
            CampaignInboundReplyItem(
                id=r.id,
                tenant_id=r.tenant_id,
                campaign_id=r.campaign_id,
                campaign_name=campaign_name,
                lead_id=r.lead_id,
                lead_name=lead_name,
                lead_phone=lead_phone,
                evolution_instance_id=r.evolution_instance_id,
                evolution_instance_label=inst_label,
                message_text=r.message_text,
                forwarded_to_webhook=r.forwarded_to_webhook,
                webhook_skip_reason=r.webhook_skip_reason,
                created_at=r.created_at,
            )
        )
    return out


@router.post("/bulk-delete")
def bulk_delete_campaigns(
    body: CampaignBulkDelete,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Exclui várias campanhas (mesmas regras de status que DELETE único)."""
    tenant_id = user.tenant_id
    deleted = 0
    errors: list[dict] = []
    for cid in body.ids:
        campaign = db.query(Campaign).filter(
            Campaign.id == cid,
            Campaign.tenant_id == tenant_id,
        ).first()
        if not campaign:
            errors.append({"id": cid, "detail": "nao_encontrada"})
            continue
        if campaign.status not in DELETABLE_CAMPAIGN_STATUSES:
            errors.append({"id": cid, "detail": f"status_{campaign.status}_nao_permite_exclusao"})
            continue
        db.delete(campaign)
        deleted += 1
    db.commit()
    return {"deleted": deleted, "errors": errors}


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retorna uma campanha por ID."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    return campaign


@router.get("/{campaign_id}/report", response_model=CampaignReportResponse)
def get_campaign_report(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    limit_messages: int = Query(500, ge=1, le=2000),
    limit_replies: int = Query(500, ge=1, le=2000),
):
    """Relatório da campanha (tentativas, falhas, respostas e métricas)."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")

    msg_rows = (
        db.query(
            CampaignMessage,
            Lead.name,
            Lead.phone,
            EvolutionInstance.display_name,
            EvolutionInstance.name,
        )
        .join(Lead, Lead.id == CampaignMessage.lead_id)
        .outerjoin(EvolutionInstance, EvolutionInstance.id == CampaignMessage.evolution_instance_id)
        .filter(CampaignMessage.campaign_id == campaign_id)
        .order_by(desc(CampaignMessage.id))
        .limit(limit_messages)
        .all()
    )
    messages: list[CampaignReportMessageItem] = []
    total_sent = 0
    total_failed = 0
    failed_without_whatsapp = 0
    for m, lead_name, lead_phone, inst_display, inst_name in msg_rows:
        if m.status == "sent":
            total_sent += 1
        elif m.status == "failed":
            total_failed += 1
            if (m.error_message or "").strip().lower().startswith("número sem whatsapp"):
                failed_without_whatsapp += 1
        messages.append(
            CampaignReportMessageItem(
                id=m.id,
                lead_id=m.lead_id,
                lead_name=lead_name,
                lead_phone=lead_phone,
                evolution_instance_id=m.evolution_instance_id,
                evolution_instance_label=((inst_display or "").strip() or (inst_name or "").strip() or None),
                status=m.status or "pending",
                error_message=m.error_message,
                sent_at=m.sent_at,
                created_at=m.created_at,
            )
        )

    reply_rows = (
        db.query(
            CampaignInboundReply,
            Lead.name,
            Lead.phone,
        )
        .join(Lead, Lead.id == CampaignInboundReply.lead_id)
        .filter(CampaignInboundReply.campaign_id == campaign_id)
        .order_by(desc(CampaignInboundReply.id))
        .limit(limit_replies)
        .all()
    )
    content = campaign.content or {}
    keywords = _extract_keywords(content)
    replies: list[CampaignReportReplyItem] = []
    positive_replies = 0
    forwarded_replies = 0
    for r, lead_name, lead_phone in reply_rows:
        matched = _matched_keyword_list(r.message_text, keywords) if keywords else []
        is_positive = bool(matched) if keywords else False
        if is_positive:
            positive_replies += 1
        if r.forwarded_to_webhook:
            forwarded_replies += 1
        replies.append(
            CampaignReportReplyItem(
                id=r.id,
                lead_id=r.lead_id,
                lead_name=lead_name,
                lead_phone=lead_phone,
                message_text=r.message_text,
                matched_keywords=matched,
                is_positive=is_positive,
                forwarded_to_webhook=r.forwarded_to_webhook,
                webhook_skip_reason=r.webhook_skip_reason,
                created_at=r.created_at,
            )
        )

    summary = CampaignReportSummary(
        total_attempts=len(msg_rows),
        total_sent=total_sent,
        total_failed=total_failed,
        total_replies=len(reply_rows),
        positive_replies=positive_replies,
        forwarded_replies=forwarded_replies,
        failed_without_whatsapp=failed_without_whatsapp,
    )
    return CampaignReportResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        campaign_status=campaign.status,
        summary=summary,
        messages=messages,
        replies=replies,
    )


@router.post("/{campaign_id}/tag-failed-contacts", response_model=CampaignTagFailedContactsResponse)
def tag_failed_contacts(
    campaign_id: int,
    body: CampaignTagFailedContactsBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Aplica tag nos contatos com falha nessa campanha (ex.: bloqueio)."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")

    tag_name = body.tag_name.strip()
    if not tag_name:
        raise HTTPException(status_code=400, detail="Nome da tag obrigatório.")
    tag = db.query(Tag).filter(Tag.tenant_id == tenant_id, Tag.name == tag_name).first()
    if not tag:
        tag = Tag(tenant_id=tenant_id, name=tag_name)
        db.add(tag)
        db.flush()

    rows = (
        db.query(CampaignMessage.lead_id)
        .join(Lead, Lead.id == CampaignMessage.lead_id)
        .filter(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.status == "failed",
            Lead.tenant_id == tenant_id,
        )
        .distinct()
        .all()
    )
    lead_ids = [lid for (lid,) in rows]
    tagged = 0
    if lead_ids:
        leads = db.query(Lead).filter(Lead.id.in_(lead_ids), Lead.tenant_id == tenant_id).all()
        for lead in leads:
            if tag not in lead.tags:
                lead.tags.append(tag)
                tagged += 1
    db.commit()
    return CampaignTagFailedContactsResponse(
        campaign_id=campaign_id,
        tag_id=tag.id,
        tag_name=tag.name,
        tagged_contacts=tagged,
        failed_contacts_found=len(lead_ids),
    )


@router.post("", response_model=CampaignResponse, status_code=201)
def create_campaign(
    body: CampaignCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Cria uma campanha (status draft)."""
    tenant_id = user.tenant_id
    # Garantir que a lista pertence ao tenant
    list_row = db.query(List).filter(
        List.id == body.list_id,
        List.tenant_id == tenant_id,
    ).first()
    if not list_row:
        raise HTTPException(status_code=400, detail="Lista não encontrada.")
    campaign = Campaign(
        tenant_id=tenant_id,
        name=body.name,
        type=body.type,
        list_id=body.list_id,
        tag_filter_include=body.tag_filter_include,
        tag_filter_exclude=body.tag_filter_exclude,
        content=_with_default_campaign_webhook(body.content),
        use_global_shielding=body.use_global_shielding,
        shielding_override=body.shielding_override,
        instance_ids=body.instance_ids,
        status="draft",
        scheduled_at=body.scheduled_at,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    body: CampaignUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Atualiza campanha (apenas se status draft)."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Só é possível editar campanha em rascunho.")
    data = body.model_dump(exclude_unset=True)
    if "list_id" in data and data["list_id"]:
        list_row = db.query(List).filter(
            List.id == data["list_id"],
            List.tenant_id == tenant_id,
        ).first()
        if not list_row:
            raise HTTPException(status_code=400, detail="Lista não encontrada.")
    for k, v in data.items():
        if k == "content":
            v = _with_default_campaign_webhook(v)
        setattr(campaign, k, v)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/media")
async def upload_campaign_media(
    campaign_id: int,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Anexa arquivo de mídia à campanha (imagem, vídeo, áudio, documento). Arquivo é salvo no servidor, não link."""
    try:
        form = await request.form()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Requisição inválida. Envie o arquivo como multipart/form-data com o campo 'file'.",
        )
    file = form.get("file")
    if not file or not hasattr(file, "read"):
        raise HTTPException(
            status_code=400,
            detail="Nenhum arquivo enviado. Selecione um arquivo (imagem, vídeo, áudio ou documento) e tente novamente.",
        )
    if hasattr(file, "filename"):
        filename = (file.filename or "").strip() or "arquivo"
    else:
        filename = "arquivo"
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Só é possível anexar mídia em campanha em rascunho.")
    content_type = (getattr(file, "content_type", None) or "").split(";")[0].strip().lower()
    if not content_type or content_type not in ALLOWED_MEDIA:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não permitido. Use: imagem (jpeg, png, gif, webp), vídeo (mp4, 3gp), áudio (ogg, mp3, m4a) ou documento (pdf, doc, docx).",
        )
    ext = EXT_FROM_MIME.get(content_type, ".bin")
    safe_name = re.sub(r"[^\w\-.]", "_", filename)[:80]
    if not safe_name.endswith(ext):
        safe_name = (safe_name or "file") + ext
    rel_dir = f"campaigns/{campaign_id}"
    dest_dir = UPLOADS_DIR / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_name
    try:
        if hasattr(file, "read"):
            read_fn = file.read
            content_bytes = await read_fn() if asyncio.iscoroutinefunction(read_fn) else read_fn()
        else:
            content_bytes = file.file.read()
    except Exception:
        content_bytes = b""
    if hasattr(file, "close") and callable(file.close):
        try:
            file.close()
        except Exception:
            pass
    if not content_bytes:
        raise HTTPException(
            status_code=400,
            detail="O arquivo está vazio. Selecione um arquivo válido e tente novamente.",
        )
    if len(content_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Arquivo maior que 50 MB.")
    dest_path.write_bytes(content_bytes)
    media_path = f"{rel_dir}/{safe_name}"
    campaign_content = dict(campaign.content or {})
    campaign_content["media_path"] = media_path
    campaign_content["media_mimetype"] = content_type
    campaign_content["media_filename"] = safe_name
    campaign.content = campaign_content
    db.commit()
    db.refresh(campaign)
    return {
        "media_path": media_path,
        "media_mimetype": content_type,
        "media_filename": safe_name,
        "campaign": campaign,
    }


@router.post("/{campaign_id}/start", status_code=202)
async def start_campaign(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Dispara a campanha em background (apenas se status draft e com lista/conteúdo)."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Só é possível disparar campanha em rascunho.")
    if not campaign.list_id:
        raise HTTPException(status_code=400, detail="Campanha sem lista definida.")
    content = campaign.content or {}
    ctype = (content.get("type") or "text").lower()
    has_text = bool(content.get("text") or content.get("caption"))
    has_media = bool(content.get("media_path") or content.get("media_base64"))
    if ctype == "text" and not has_text:
        raise HTTPException(status_code=400, detail="Defina o texto da mensagem antes de disparar.")
    if ctype in ("image", "video", "audio", "document") and not has_media:
        raise HTTPException(status_code=400, detail="Anexe o arquivo de mídia (imagem/vídeo/áudio/documento) antes de disparar.")
    if ctype in ("image", "video", "audio", "document") and not has_text:
        pass  # legenda opcional
    asyncio.create_task(asyncio.to_thread(run_campaign_sync, campaign_id, tenant_id))
    logger.info(
        "campaign_disparo_iniciado tenant_id=%s campaign_id=%s",
        tenant_id,
        campaign_id,
    )
    return {"message": "Campanha em disparo."}


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove campanha (apenas se status draft ou cancelled)."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    if campaign.status not in DELETABLE_CAMPAIGN_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Só é possível excluir campanha em rascunho, agendada, concluída ou cancelada (não em andamento).",
        )
    db.delete(campaign)
    db.commit()
