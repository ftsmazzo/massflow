"""
Listas (agrupamento de contatos). CRUD e add/remove contatos.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.lead import Lead
from app.models.list import List
from app.schemas.list_schema import (
    ListCreate,
    ListUpdate,
    ListResponse,
    ListWithContactsResponse,
    ListAddContactsBody,
    ListRemoveContactsBody,
)
from app.routers.contacts import _lead_to_response
from app.schemas.contact import ContactResponse

router = APIRouter(prefix="/lists", tags=["Lists"])


@router.get("", response_model=list[ListWithContactsResponse])
def list_lists(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Lista listas do tenant com contagem de contatos."""
    tenant_id = user.tenant_id
    lists = db.query(List).filter(List.tenant_id == tenant_id).all()
    return [
        ListWithContactsResponse(
            id=lst.id,
            tenant_id=lst.tenant_id,
            name=lst.name,
            created_at=lst.created_at,
            updated_at=lst.updated_at,
            contact_count=len(lst.leads),
        )
        for lst in lists
    ]


@router.get("/{list_id}", response_model=ListWithContactsResponse)
def get_list(
    list_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retorna uma lista por ID."""
    tenant_id = user.tenant_id
    lst = db.query(List).filter(List.id == list_id, List.tenant_id == tenant_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    return ListWithContactsResponse(
        id=lst.id,
        tenant_id=lst.tenant_id,
        name=lst.name,
        created_at=lst.created_at,
        updated_at=lst.updated_at,
        contact_count=len(lst.leads),
    )


@router.get("/{list_id}/contacts", response_model=list[ContactResponse])
def list_contacts_in_list(
    list_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Lista contatos que pertencem à lista."""
    tenant_id = user.tenant_id
    lst = db.query(List).filter(List.id == list_id, List.tenant_id == tenant_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    return [_lead_to_response(lead) for lead in lst.leads]


@router.post("", response_model=ListResponse, status_code=201)
def create_list(
    body: ListCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Cria uma lista."""
    tenant_id = user.tenant_id
    lst = List(tenant_id=tenant_id, name=body.name.strip())
    db.add(lst)
    db.commit()
    db.refresh(lst)
    return lst


@router.patch("/{list_id}", response_model=ListResponse)
def update_list(
    list_id: int,
    body: ListUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Atualiza nome da lista."""
    tenant_id = user.tenant_id
    lst = db.query(List).filter(List.id == list_id, List.tenant_id == tenant_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    if body.name is not None:
        lst.name = body.name.strip()
    db.commit()
    db.refresh(lst)
    return lst


@router.delete("/{list_id}", status_code=204)
def delete_list(
    list_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove a lista (não remove os contatos)."""
    tenant_id = user.tenant_id
    lst = db.query(List).filter(List.id == list_id, List.tenant_id == tenant_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    db.delete(lst)
    db.commit()
    return None


@router.post("/{list_id}/contacts")
def add_contacts_to_list(
    list_id: int,
    body: ListAddContactsBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Adiciona contatos à lista."""
    tenant_id = user.tenant_id
    lst = db.query(List).filter(List.id == list_id, List.tenant_id == tenant_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    leads = db.query(Lead).filter(Lead.id.in_(body.contact_ids), Lead.tenant_id == tenant_id).all()
    added = 0
    for lead in leads:
        if lst not in lead.lists:
            lead.lists.append(lst)
            added += 1
    db.commit()
    return {"added": added, "list_id": list_id}


@router.delete("/{list_id}/contacts")
def remove_contacts_from_list(
    list_id: int,
    body: ListRemoveContactsBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Remove contatos da lista."""
    tenant_id = user.tenant_id
    lst = db.query(List).filter(List.id == list_id, List.tenant_id == tenant_id).first()
    if not lst:
        raise HTTPException(status_code=404, detail="Lista não encontrada.")
    leads = db.query(Lead).filter(Lead.id.in_(body.contact_ids), Lead.tenant_id == tenant_id).all()
    removed = 0
    for lead in leads:
        if lst in lead.lists:
            lead.lists.remove(lst)
            removed += 1
    db.commit()
    return {"removed": removed, "list_id": list_id}
