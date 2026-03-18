"""
Campanhas: CRUD, criação e disparo em background.
"""
import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.list import List
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from app.services.campaign_sender import run_campaign_sync

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


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
    if not content.get("text") and not content.get("caption"):
        raise HTTPException(status_code=400, detail="Defina o conteúdo (texto ou legenda) antes de disparar.")
    asyncio.create_task(asyncio.to_thread(run_campaign_sync, campaign_id, tenant_id))
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
    if campaign.status not in ("draft", "cancelled"):
        raise HTTPException(status_code=400, detail="Só é possível excluir campanha em rascunho ou cancelada.")
    db.delete(campaign)
    db.commit()
