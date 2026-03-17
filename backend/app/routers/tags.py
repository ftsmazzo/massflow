"""
Tags (funis e segmentação). CRUD e aplicar em contatos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate, TagResponse, TagApplyBody

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("", response_model=list[TagResponse])
def list_tags(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Lista tags do tenant."""
    tenant_id = user.tenant_id
    tags = db.query(Tag).filter(Tag.tenant_id == tenant_id).all()
    return tags


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    tag_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retorna uma tag por ID."""
    tenant_id = user.tenant_id
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    return tag


@router.post("", response_model=TagResponse, status_code=201)
def create_tag(
    body: TagCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Cria uma tag (nome único por tenant)."""
    tenant_id = user.tenant_id
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da tag obrigatório.")
    existing = db.query(Tag).filter(Tag.tenant_id == tenant_id, Tag.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Já existe uma tag com este nome.")
    tag = Tag(tenant_id=tenant_id, name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
def update_tag(
    tag_id: int,
    body: TagUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Atualiza nome da tag."""
    tenant_id = user.tenant_id
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    new_name = body.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Nome da tag obrigatório.")
    other = db.query(Tag).filter(Tag.tenant_id == tenant_id, Tag.name == new_name, Tag.id != tag_id).first()
    if other:
        raise HTTPException(status_code=400, detail="Já existe outra tag com este nome.")
    tag.name = new_name
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    tag_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove a tag (desassocia dos contatos)."""
    tenant_id = user.tenant_id
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    db.delete(tag)
    db.commit()
    return None


@router.post("/{tag_id}/apply")
def apply_tag_to_contacts(
    tag_id: int,
    body: TagApplyBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Aplica a tag aos contatos informados."""
    tenant_id = user.tenant_id
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.tenant_id == tenant_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag não encontrada.")
    leads = db.query(Lead).filter(Lead.id.in_(body.contact_ids), Lead.tenant_id == tenant_id).all()
    applied = 0
    for lead in leads:
        if tag not in lead.tags:
            lead.tags.append(tag)
            applied += 1
    db.commit()
    return {"applied": applied, "tag_id": tag_id}
