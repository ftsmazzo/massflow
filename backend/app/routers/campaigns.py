"""
Campanhas: CRUD, criação, upload de mídia (arquivo anexado) e disparo em background.
"""
import asyncio
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.lead import Lead
from app.models.list import List
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from app.services.campaign_sender import run_campaign_sync
from app.services.chatwoot_webhook_payload import resolve_outbound_payload
from app.services.inbound_evolution import (
    extract_inbound_text_and_phone,
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


def _fold_accents(s: str) -> str:
    """Remove acentos para comparar palavras-chave com respostas do usuário."""
    nfd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _extract_keywords(content: dict) -> list[str]:
    raw = content.get("response_keywords")
    if isinstance(raw, list):
        return [str(k).strip().lower() for k in raw if str(k).strip()]
    if isinstance(raw, str):
        return [k.strip().lower() for k in raw.split(",") if k.strip()]
    return []


def _contains_interest_keyword(text: str, keywords: list[str]) -> bool:
    txt = _fold_accents((text or "").strip().lower())
    if not txt or not keywords:
        return False
    return any(_fold_accents(k) in txt for k in keywords)


def _matched_keyword_list(text: str, keywords: list[str]) -> list[str]:
    """Lista palavras-chave originais que aparecem no texto (comparação sem acento)."""
    txt = _fold_accents((text or "").strip().lower())
    out: list[str] = []
    for k in keywords:
        if _fold_accents(k) in txt and k not in out:
            out.append(k)
    return out


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
        content=body.content,
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
    return {"message": "Campanha em disparo."}


@router.post("/inbound/{tenant_id}")
async def inbound_campaign_reply(
    tenant_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    debug: Annotated[bool, Query(False, description="Inclui dados de diagnóstico na resposta (uso em testes)")],
):
    """
    Recebe resposta inbound (ex.: Evolution webhook) e encaminha para webhook IA
    quando a mensagem do lead contém palavra-chave de interesse configurada.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Payload JSON inválido.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload deve ser objeto JSON.")

    extracted = extract_inbound_text_and_phone(payload)
    if not extracted:
        out: dict = {"matched": False, "forwarded": False, "reason": "sem_texto_ou_telefone"}
        if debug:
            out["debug"] = {
                "event": payload.get("event"),
                "top_level_keys": list(payload.keys()),
                "hint": "Configure o webhook da Evolution para POST nesta URL e evento MESSAGES_UPSERT (messages.upsert).",
            }
        return out

    inbound_text, inbound_phone = extracted

    tenant_leads = db.query(Lead).filter(Lead.tenant_id == tenant_id).all()
    lead = next((l for l in tenant_leads if phones_match_for_lead(inbound_phone, l.phone)), None)
    if not lead:
        out = {"matched": False, "forwarded": False, "reason": "lead_nao_encontrado"}
        if debug:
            out["debug"] = {
                "inbound_phone_normalized": inbound_phone,
                "sample_lead_phones": [normalize_phone_digits(l.phone) for l in tenant_leads[:5]],
            }
        return out
    lead.last_response_at = datetime.utcnow()
    db.commit()

    latest_msg = (
        db.query(CampaignMessage)
        .join(Campaign, Campaign.id == CampaignMessage.campaign_id)
        .filter(
            Campaign.tenant_id == tenant_id,
            CampaignMessage.lead_id == lead.id,
            CampaignMessage.status == "sent",
        )
        .order_by(desc(CampaignMessage.sent_at), desc(CampaignMessage.id))
        .first()
    )
    if not latest_msg:
        return {"matched": False, "forwarded": False, "reason": "sem_disparo_previo"}

    campaign = db.query(Campaign).filter(
        Campaign.id == latest_msg.campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        return {"matched": False, "forwarded": False, "reason": "campanha_nao_encontrada"}

    content = campaign.content or {}
    webhook_url = str(content.get("response_webhook_url") or "").strip()
    keywords = _extract_keywords(content)
    if not webhook_url:
        return {"matched": False, "forwarded": False, "reason": "webhook_nao_configurado"}
    if not keywords:
        return {"matched": False, "forwarded": False, "reason": "keywords_nao_configuradas"}
    if not _contains_interest_keyword(inbound_text, keywords):
        return {"matched": False, "forwarded": False, "reason": "sem_keyword"}

    matched_kw = _matched_keyword_list(inbound_text, keywords)
    lead_display_name = (lead.name or "").strip() or "Contato"
    outbound_payload = resolve_outbound_payload(
        content,
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        lead_id=lead.id,
        lead_name=lead_display_name,
        lead_phone=lead.phone,
        inbound_text=inbound_text,
        matched_keywords=matched_kw,
    )
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(webhook_url, json=outbound_payload)
            resp.raise_for_status()
    except Exception as e:
        return {
            "matched": True,
            "forwarded": False,
            "reason": "erro_ao_enviar_webhook",
            "error": str(e)[:500],
        }
    return {"matched": True, "forwarded": True}


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
    if campaign.status not in ("draft", "cancelled"):
        raise HTTPException(status_code=400, detail="Só é possível excluir campanha em rascunho ou cancelada.")
    db.delete(campaign)
    db.commit()
