"""
Tags (funis e segmentação). CRUD e aplicar em contatos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.models.list import List
from app.models.tag import Tag
from app.models.associations import list_leads, lead_tags
from app.schemas.tag import (
    TagCreate,
    TagUpdate,
    TagResponse,
    TagApplyBody,
    TagBulkUpdateBody,
    TagBulkUpdateResponse,
)

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


_MAX_BULK_LEADS = 5000


@router.post("/bulk-update", response_model=TagBulkUpdateResponse)
def bulk_update_tags(
    body: TagBulkUpdateBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Atualiza tags em massa com filtros:

    - **list_id**: restringe a contatos que estão nessa lista.
    - **contact_ids**: restringe a esses IDs (intersecção com lista, se ambos).
    - **require_all_tag_ids**: só contatos que têm **todas** essas tags.
    - **without_any_tag_ids**: exclui contatos que têm **qualquer uma** dessas tags.
    - **add_tag_ids** / **remove_tag_ids**: tags a incluir ou retirar.

    Limite de 5000 contatos por requisição.
    """
    tenant_id = user.tenant_id

    req_all = list(dict.fromkeys(body.require_all_tag_ids))
    wo_any = list(dict.fromkeys(body.without_any_tag_ids))
    add_ids = list(dict.fromkeys(body.add_tag_ids))
    rem_ids = list(dict.fromkeys(body.remove_tag_ids))

    all_tag_ids = set(req_all) | set(wo_any) | set(add_ids) | set(rem_ids)
    if all_tag_ids:
        found = db.query(Tag.id).filter(Tag.tenant_id == tenant_id, Tag.id.in_(all_tag_ids)).all()
        found_ids = {row[0] for row in found}
        missing = all_tag_ids - found_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Tags inválidas ou de outro tenant: {sorted(missing)}")

    if body.list_id is not None:
        lst = db.query(List).filter(List.id == body.list_id, List.tenant_id == tenant_id).first()
        if not lst:
            raise HTTPException(status_code=404, detail="Lista não encontrada.")

    q = db.query(Lead).filter(Lead.tenant_id == tenant_id)

    if body.list_id is not None:
        q = q.join(list_leads, Lead.id == list_leads.c.lead_id).filter(list_leads.c.list_id == body.list_id)

    if body.contact_ids:
        q = q.filter(Lead.id.in_(body.contact_ids))

    if req_all:
        n_req = len(req_all)
        subq = (
            db.query(lead_tags.c.lead_id)
            .filter(lead_tags.c.tag_id.in_(req_all))
            .group_by(lead_tags.c.lead_id)
            .having(func.count(lead_tags.c.lead_id) == n_req)
        )
        q = q.filter(Lead.id.in_(subq))

    if wo_any:
        has_excluded = exists(
            select(1).select_from(lead_tags).where(
                and_(
                    lead_tags.c.lead_id == Lead.id,
                    lead_tags.c.tag_id.in_(wo_any),
                )
            )
        )
        q = q.filter(~has_excluded)

    q = q.distinct()
    id_rows = q.with_entities(Lead.id).distinct().limit(_MAX_BULK_LEADS + 1).all()
    capped = len(id_rows) > _MAX_BULK_LEADS
    ids = [r[0] for r in id_rows[:_MAX_BULK_LEADS]]
    if not ids:
        return TagBulkUpdateResponse(
            matched_leads=0,
            tags_added_links=0,
            tags_removed_links=0,
            capped=capped,
        )
    leads = (
        db.query(Lead)
        .filter(Lead.id.in_(ids), Lead.tenant_id == tenant_id)
        .options(joinedload(Lead.tags))
        .all()
    )

    add_tags = (
        db.query(Tag).filter(Tag.tenant_id == tenant_id, Tag.id.in_(add_ids)).all()
        if add_ids
        else []
    )
    remove_tags = (
        db.query(Tag).filter(Tag.tenant_id == tenant_id, Tag.id.in_(rem_ids)).all()
        if rem_ids
        else []
    )
    add_by_id = {t.id: t for t in add_tags}
    remove_by_id = {t.id: t for t in remove_tags}

    added_links = 0
    removed_links = 0
    for lead in leads:
        for tid in rem_ids:
            t = remove_by_id.get(tid)
            if t and t in lead.tags:
                lead.tags.remove(t)
                removed_links += 1
        for tid in add_ids:
            t = add_by_id.get(tid)
            if t and t not in lead.tags:
                lead.tags.append(t)
                added_links += 1

    db.commit()
    return TagBulkUpdateResponse(
        matched_leads=len(leads),
        tags_added_links=added_links,
        tags_removed_links=removed_links,
        capped=capped,
    )
