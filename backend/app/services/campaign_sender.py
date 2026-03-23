"""
Disparo de campanha: envia mensagens para os leads da lista via Evolution API.
Suporta texto e mídia (imagem/vídeo/áudio/documento) anexada como arquivo (base64), não link.
"""
import base64
import logging
import random
import time
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.campaign import Campaign
from app.models.campaign_message import CampaignMessage
from app.models.lead import Lead
from app.models.list import List
from app.models.evolution_instance import EvolutionInstance
from app.models.associations import list_leads, lead_tags
from app.models.tag import Tag
from app.models.shielding_config import TenantShieldingConfig
from app.services.evolution import send_text_sync, send_media_sync

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MEDIATYPE_MAP = {"image": "Image", "video": "Video", "audio": "Audio", "document": "Document"}
logger = logging.getLogger(__name__)


def _campaign_n8n_url(content: dict) -> str:
    return str(
        content.get("campaign_webhook_url")
        or content.get("response_webhook_url")
        or ""
    ).strip()


def _post_webhook_message_sent(
    webhook_url: str,
    *,
    tenant_id: int,
    campaign: Campaign,
    lead: Lead,
    message_text: str,
    content_type: str,
) -> None:
    """Notifica n8n após cada envio bem-sucedido (não interrompe o disparo se falhar)."""
    payload = {
        "event": "campaign_message_sent",
        "tenant_id": tenant_id,
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "lead_id": lead.id,
        "lead_name": (lead.name or "").strip() or "Contato",
        "lead_phone": lead.phone,
        "message_text": message_text,
        "content_type": content_type,
        "source": "massflow",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info(
            "campaign_send_webhook_ok tenant_id=%s campaign_id=%s lead_id=%s",
            tenant_id,
            campaign.id,
            lead.id,
        )
    except Exception as e:
        logger.warning(
            "campaign_send_webhook_falhou tenant_id=%s campaign_id=%s lead_id=%s err=%s",
            tenant_id,
            campaign.id,
            lead.id,
            str(e)[:400],
        )


def _resolve_text(text: str, lead: Lead) -> str:
    """Substitui variáveis {nome}, {telefone}, {email} pelo valor do lead."""
    if not text:
        return text
    out = text
    out = out.replace("{nome}", (lead.name or "").strip() or "Contato")
    out = out.replace("{telefone}", lead.phone or "")
    out = out.replace("{email}", (lead.email or "").strip() or "")
    return out


def _get_delay_sec(config: dict) -> tuple[int, int]:
    """Retorna (min_sec, max_sec) da config de blindagem."""
    delays = config.get("delays") or {}
    return (
        int(delays.get("min_sec", 20)),
        int(delays.get("max_sec", 45)),
    )


def run_campaign_sync(campaign_id: int, tenant_id: int) -> None:
    """
    Executa o disparo da campanha (síncrono, rodar em thread).
    Atualiza campaign.status para running e depois completed.
    """
    db = SessionLocal()
    try:
        campaign = (
            db.query(Campaign)
            .filter(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
            .first()
        )
        if not campaign or campaign.status != "draft":
            return

        campaign.status = "running"
        campaign.started_at = datetime.utcnow()
        db.commit()

        list_row = db.query(List).filter(
            List.id == campaign.list_id,
            List.tenant_id == tenant_id,
        ).first()
        if not list_row:
            campaign.status = "draft"
            db.commit()
            return

        leads_query = (
            db.query(Lead)
            .join(list_leads, and_(list_leads.c.lead_id == Lead.id, list_leads.c.list_id == campaign.list_id))
            .filter(Lead.tenant_id == tenant_id, Lead.opt_in == True)
        )
        if campaign.tag_filter_include:
            tag_names_include = list(campaign.tag_filter_include)
            leads_query = leads_query.join(lead_tags).join(Tag).filter(
                Tag.tenant_id == tenant_id,
                Tag.name.in_(tag_names_include),
            )
        if campaign.tag_filter_exclude:
            tag_names_exclude = list(campaign.tag_filter_exclude)
            subq = (
                db.query(lead_tags.c.lead_id)
                .join(Tag, Tag.id == lead_tags.c.tag_id)
                .filter(Tag.tenant_id == tenant_id, Tag.name.in_(tag_names_exclude))
            )
            leads_query = leads_query.filter(~Lead.id.in_(subq))
        leads_query = leads_query.distinct()
        leads = leads_query.all()
        logger.info(
            "campaign_disparo tenant_id=%s campaign_id=%s leads_total=%s",
            tenant_id,
            campaign_id,
            len(leads),
        )

        instance_ids = campaign.instance_ids if isinstance(campaign.instance_ids, list) else None
        if instance_ids:
            instances = (
                db.query(EvolutionInstance)
                .filter(
                    EvolutionInstance.tenant_id == tenant_id,
                    EvolutionInstance.id.in_(instance_ids),
                    EvolutionInstance.status.in_(["open", "connected"]),
                )
                .all()
            )
        else:
            instances = (
                db.query(EvolutionInstance)
                .filter(
                    EvolutionInstance.tenant_id == tenant_id,
                    EvolutionInstance.status.in_(["open", "connected"]),
                )
                .all()
            )

        if not instances:
            campaign.status = "draft"
            db.commit()
            return

        if not campaign.use_global_shielding and campaign.shielding_override:
            config = campaign.shielding_override or {}
        else:
            shielding_row = db.query(TenantShieldingConfig).filter(
                TenantShieldingConfig.tenant_id == tenant_id,
            ).first()
            config = (shielding_row.config or {}) if shielding_row else {}
        min_sec, max_sec = _get_delay_sec(config)

        content = campaign.content or {}
        webhook_url = _campaign_n8n_url(content)
        content_type = (content.get("type") or "text").lower()
        text_template = content.get("text") or content.get("caption") or ""
        caption_template = str(content.get("caption") or content.get("text") or "")

        # Para mídia: obter base64 do arquivo anexado (media_path) ou já em content (media_base64)
        media_base64: str | None = None
        media_mimetype = content.get("media_mimetype") or "image/jpeg"
        media_filename = content.get("media_filename") or "image.jpg"
        if content_type in ("image", "video", "audio", "document"):
            if content.get("media_base64"):
                media_base64 = content["media_base64"]
            elif content.get("media_path"):
                file_path = UPLOADS_DIR / content["media_path"]
                if file_path.is_file():
                    media_base64 = base64.b64encode(file_path.read_bytes()).decode("ascii")
                else:
                    media_base64 = None
            if not media_base64:
                campaign.status = "draft"
                db.commit()
                return  # mídia obrigatória para tipo image/video/audio/document não encontrada

        for i, lead in enumerate(leads):
            inst = instances[i % len(instances)]
            try:
                if content_type == "text":
                    text = _resolve_text(text_template, lead)
                    if not text.strip():
                        continue
                    result = send_text_sync(
                        inst.api_url,
                        inst.api_key or "",
                        inst.name,
                        lead.phone,
                        text,
                    )
                    sent_body = text
                else:
                    caption = _resolve_text(caption_template, lead)
                    mediatype = MEDIATYPE_MAP.get(content_type, "Image")
                    result = send_media_sync(
                        inst.api_url,
                        inst.api_key or "",
                        inst.name,
                        lead.phone,
                        mediatype,
                        media_mimetype,
                        caption,
                        media_base64,
                        media_filename,
                    )
                    sent_body = caption or ""
                msg_id = None
                if isinstance(result, dict) and "key" in result and isinstance(result["key"], dict):
                    msg_id = result["key"].get("id")
                cm = CampaignMessage(
                    campaign_id=campaign.id,
                    lead_id=lead.id,
                    evolution_instance_id=inst.id,
                    message_id=msg_id,
                    status="sent",
                    sent_at=datetime.utcnow(),
                )
                db.add(cm)
                lead.last_sent_at = datetime.utcnow()
                db.commit()
                if webhook_url:
                    _post_webhook_message_sent(
                        webhook_url,
                        tenant_id=tenant_id,
                        campaign=campaign,
                        lead=lead,
                        message_text=sent_body,
                        content_type=content_type,
                    )
            except Exception as e:
                cm = CampaignMessage(
                    campaign_id=campaign.id,
                    lead_id=lead.id,
                    evolution_instance_id=inst.id,
                    status="failed",
                    error_message=str(e)[:500],
                )
                db.add(cm)
                db.commit()

            if i < len(leads) - 1:
                delay = random.randint(min_sec, max_sec)
                time.sleep(delay)

        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()
        db.commit()
        logger.info(
            "campaign_disparo_concluido tenant_id=%s campaign_id=%s leads_total=%s",
            tenant_id,
            campaign_id,
            len(leads),
        )
    finally:
        db.close()
