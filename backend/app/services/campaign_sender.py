"""
Disparo de campanha: envia mensagens para os leads da lista via Evolution API.
Executado em thread em background (não bloqueia o request).
"""
import random
import time
from datetime import datetime

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
from app.services.evolution import send_text_sync


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
        content_type = (content.get("type") or "text").lower()
        text_template = content.get("text") or content.get("caption") or ""

        for i, lead in enumerate(leads):
            inst = instances[i % len(instances)]
            text = _resolve_text(text_template, lead) if content_type == "text" else _resolve_text(str(content.get("caption") or content.get("text") or ""), lead)
            if not text.strip():
                continue
            try:
                result = send_text_sync(
                    inst.api_url,
                    inst.api_key or "",
                    inst.name,
                    lead.phone,
                    text,
                )
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
    finally:
        db.close()
