"""
Contatos (Lead = contato físico). CRUD, filtros e sync para API externa.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.models.list import List
from app.models.tag import Tag
from app.models.associations import list_leads, lead_tags
from app.schemas.contact import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactSyncBody,
    ContactSyncResponse,
    ContactBulkDeleteBody,
    ContactBulkDeleteResponse,
)

router = APIRouter(prefix="/contacts", tags=["Contacts"])


def _lead_to_response(lead: Lead) -> ContactResponse:
    """Converte Lead para ContactResponse com tags e list_ids."""
    tag_names = [t.name for t in lead.tags]
    list_ids = [lst.id for lst in lead.lists]
    return ContactResponse(
        id=lead.id,
        tenant_id=lead.tenant_id,
        phone=lead.phone,
        name=lead.name,
        email=lead.email,
        custom_fields=lead.custom_fields or {},
        opt_in=lead.opt_in,
        status=lead.status or "ativo",
        tags=tag_names,
        list_ids=list_ids,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        last_sent_at=lead.last_sent_at,
        last_response_at=lead.last_response_at,
    )


@router.get("", response_model=list[ContactResponse])
def list_contacts(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    list_id: int | None = Query(None, description="Filtrar por lista"),
    tags: str | None = Query(None, description="Tags separadas por vírgula (ex: quente,interessado)"),
    updated_since: str | None = Query(None, description="ISO datetime (contatos atualizados após)"),
    status: str | None = Query(None, description="status: ativo, na_esteira, opt_out"),
    opt_in: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista contatos do tenant com filtros (pull para sistemas externos)."""
    tenant_id = user.tenant_id
    q = db.query(Lead).filter(Lead.tenant_id == tenant_id)

    if list_id is not None:
        q = q.join(list_leads).filter(list_leads.c.list_id == list_id)
    if tags:
        tag_names = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_names:
            q = q.join(lead_tags).join(Tag).filter(
                and_(Tag.tenant_id == tenant_id, Tag.name.in_(tag_names))
            )
    if updated_since:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(updated_since.replace("Z", "+00:00"))
            q = q.filter(Lead.updated_at >= dt)
        except ValueError:
            pass
    if status is not None:
        q = q.filter(Lead.status == status)
    if opt_in is not None:
        q = q.filter(Lead.opt_in == opt_in)

    q = q.options(joinedload(Lead.tags), joinedload(Lead.lists)).distinct().offset(offset).limit(limit)
    leads = q.all()
    return [_lead_to_response(l) for l in leads]


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retorna um contato por ID."""
    tenant_id = user.tenant_id
    lead = (
        db.query(Lead)
        .options(joinedload(Lead.tags), joinedload(Lead.lists))
        .filter(Lead.id == contact_id, Lead.tenant_id == tenant_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    return _lead_to_response(lead)


@router.post("", response_model=ContactResponse, status_code=201)
def create_contact(
    body: ContactCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Cria ou atualiza contato por telefone (upsert)."""
    tenant_id = user.tenant_id
    phone = body.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Telefone obrigatório.")
    existing = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.phone == phone).first()
    if existing:
        existing.name = body.name or existing.name
        existing.email = body.email if body.email is not None else existing.email
        existing.custom_fields = body.custom_fields or existing.custom_fields
        existing.opt_in = body.opt_in
        db.commit()
        db.refresh(existing)
        return _lead_to_response(existing)
    lead = Lead(
        tenant_id=tenant_id,
        phone=phone,
        name=body.name,
        email=body.email,
        custom_fields=body.custom_fields,
        opt_in=body.opt_in,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _lead_to_response(lead)


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    body: ContactUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Atualiza contato parcialmente."""
    tenant_id = user.tenant_id
    lead = db.query(Lead).filter(Lead.id == contact_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    if body.name is not None:
        lead.name = body.name
    if body.email is not None:
        lead.email = body.email
    if body.custom_fields is not None:
        lead.custom_fields = body.custom_fields
    if body.opt_in is not None:
        lead.opt_in = body.opt_in
    if body.status is not None:
        lead.status = body.status
    if body.tag_ids is not None:
        tags = (
            db.query(Tag)
            .filter(Tag.tenant_id == tenant_id, Tag.id.in_(body.tag_ids))
            .all()
        )
        lead.tags = tags
    db.commit()
    db.refresh(lead)
    return _lead_to_response(lead)


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove contato."""
    tenant_id = user.tenant_id
    lead = db.query(Lead).filter(Lead.id == contact_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    db.delete(lead)
    db.commit()
    return None


@router.post("/bulk-delete", response_model=ContactBulkDeleteResponse)
def bulk_delete_contacts(
    body: ContactBulkDeleteBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove contatos em lote (somente do tenant logado)."""
    tenant_id = user.tenant_id
    deleted = 0
    errors: list[dict] = []
    seen: set[int] = set()

    for contact_id in body.ids:
        if contact_id in seen:
            continue
        seen.add(contact_id)
        lead = db.query(Lead).filter(Lead.id == contact_id, Lead.tenant_id == tenant_id).first()
        if not lead:
            errors.append({"id": contact_id, "detail": "Contato não encontrado."})
            continue
        db.delete(lead)
        deleted += 1

    db.commit()
    return ContactBulkDeleteResponse(deleted=deleted, errors=errors)


@router.post("/sync", response_model=ContactSyncResponse)
def sync_contacts(
    body: ContactSyncBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Sincroniza contatos (push). Upsert por telefone; cria tags se não existir; associa a lista se list_id informado."""
    tenant_id = user.tenant_id
    created = 0
    updated = 0
    errors: list[dict] = []

    for i, item in enumerate(body.contacts):
        phone = (item.phone or "").strip()
        if not phone:
            errors.append({"index": i, "phone": item.phone, "error": "Telefone vazio"})
            continue
        try:
            lead = db.query(Lead).filter(Lead.tenant_id == tenant_id, Lead.phone == phone).first()
            if lead:
                lead.name = item.name if item.name is not None else lead.name
                lead.email = item.email if item.email is not None else lead.email
                lead.custom_fields = item.custom_fields if item.custom_fields else lead.custom_fields
                lead.opt_in = item.opt_in
                updated += 1
            else:
                lead = Lead(
                    tenant_id=tenant_id,
                    phone=phone,
                    name=item.name,
                    email=item.email,
                    custom_fields=item.custom_fields,
                    opt_in=item.opt_in,
                )
                db.add(lead)
                db.flush()
                created += 1

            # Tags: criar se não existir e associar
            for tag_name in (item.tags or []):
                tag_name = (tag_name or "").strip()
                if not tag_name:
                    continue
                tag = db.query(Tag).filter(Tag.tenant_id == tenant_id, Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(tenant_id=tenant_id, name=tag_name)
                    db.add(tag)
                    db.flush()
                if tag not in lead.tags:
                    lead.tags.append(tag)

            # Lista
            if item.list_id is not None:
                lst = db.query(List).filter(List.id == item.list_id, List.tenant_id == tenant_id).first()
                if lst and lst not in lead.lists:
                    lead.lists.append(lst)
        except Exception as e:
            errors.append({"index": i, "phone": phone, "error": str(e)})

    db.commit()
    return ContactSyncResponse(created=created, updated=updated, errors=errors)
