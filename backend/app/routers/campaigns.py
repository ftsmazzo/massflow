"""
Campanhas: CRUD, criação, upload de mídia (arquivo anexado) e disparo em background.
"""
import asyncio
import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.list import List
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from app.services.campaign_sender import run_campaign_sync

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
def upload_campaign_media(
    campaign_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
):
    """Anexa arquivo de mídia à campanha (imagem, vídeo, áudio, documento). Arquivo é salvo no servidor, não link."""
    tenant_id = user.tenant_id
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha não encontrada.")
    if campaign.status != "draft":
        raise HTTPException(status_code=400, detail="Só é possível anexar mídia em campanha em rascunho.")
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in ALLOWED_MEDIA:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de arquivo não permitido. Use: imagem (jpeg, png, gif, webp), vídeo (mp4, 3gp), áudio (ogg, mp3, m4a) ou documento (pdf, doc, docx).",
        )
    ext = EXT_FROM_MIME.get(ct, ".bin")
    safe_name = re.sub(r"[^\w\-.]", "_", file.filename or "file")[:80]
    if not safe_name.endswith(ext):
        safe_name = (safe_name or "file") + ext
    rel_dir = f"campaigns/{campaign_id}"
    dest_dir = UPLOADS_DIR / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / safe_name
    try:
        content_bytes = file.file.read()
        if len(content_bytes) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Arquivo maior que 25 MB.")
        dest_path.write_bytes(content_bytes)
    finally:
        file.file.close()
    media_path = f"{rel_dir}/{safe_name}"
    campaign_content = dict(campaign.content or {})
    campaign_content["media_path"] = media_path
    campaign_content["media_mimetype"] = ct
    campaign_content["media_filename"] = safe_name
    campaign.content = campaign_content
    db.commit()
    db.refresh(campaign)
    return {
        "media_path": media_path,
        "media_mimetype": ct,
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
