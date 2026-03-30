"""
Resolve qual campanha usar para qualificação/reconciliação quando o contexto de recepção
não trouxe campaign_id: usa o último registro em campaign_inbound_replies (disparo recente).
"""
from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.campaign_inbound_reply import CampaignInboundReply
from app.models.lead import Lead
from app.services import qualification_service as qs


def resolve_lead(db: Session, tenant_id: int, lead_phone: str, lead_id: int | None) -> Lead | None:
    phone = qs.normalize_phone(lead_phone)
    if not phone:
        return None
    if lead_id is not None:
        row = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        if row:
            return row
    for row in db.query(Lead).filter(Lead.tenant_id == tenant_id).all():
        if qs.normalize_phone(row.phone) == phone:
            return row
    return None


def resolve_campaign_id_from_latest_inbound(
    db: Session,
    tenant_id: int,
    lead: Lead,
) -> int | None:
    """Última resposta inbound deste lead no tenant (campanha atual do disparo)."""
    row = (
        db.query(CampaignInboundReply)
        .filter(
            CampaignInboundReply.tenant_id == tenant_id,
            CampaignInboundReply.lead_id == lead.id,
        )
        .order_by(desc(CampaignInboundReply.created_at), desc(CampaignInboundReply.id))
        .first()
    )
    return row.campaign_id if row else None


def resolve_campaign_id_for_qualification(
    db: Session,
    tenant_id: int,
    lead_phone: str,
    lead_id: int | None,
    reception_campaign_id: int | None,
) -> int | None:
    """
    Ordem: campaign_id do reception_context se existir; senão último campaign_inbound_replies.
    """
    if reception_campaign_id is not None:
        return reception_campaign_id
    lead = resolve_lead(db, tenant_id, lead_phone, lead_id)
    if not lead:
        return None
    return resolve_campaign_id_from_latest_inbound(db, tenant_id, lead)


def mark_latest_inbound_agent_context_consumed(
    db: Session,
    tenant_id: int,
    campaign_id: int,
    lead_phone: str,
    lead_id: int | None,
) -> bool:
    """
    Marca o inbound mais recente deste lead+campanha: agente já consumiu GET next-first-interaction.
    """
    lid = lead_id
    if lid is None:
        lead = resolve_lead(db, tenant_id, lead_phone, None)
        if not lead:
            return False
        lid = lead.id
    row = (
        db.query(CampaignInboundReply)
        .filter(
            CampaignInboundReply.tenant_id == tenant_id,
            CampaignInboundReply.lead_id == lid,
            CampaignInboundReply.campaign_id == campaign_id,
        )
        .order_by(desc(CampaignInboundReply.created_at), desc(CampaignInboundReply.id))
        .first()
    )
    if not row:
        return False
    row.agent_context_consumed = True
    db.commit()
    return True
