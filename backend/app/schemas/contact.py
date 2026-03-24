"""
Schemas para Contatos (Lead = contato físico).
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    """Criação de contato (upsert por phone)."""
    phone: str = Field(..., min_length=1, max_length=20)
    name: str | None = None
    email: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    opt_in: bool = True


class ContactUpdate(BaseModel):
    """Atualização parcial de contato."""
    name: str | None = None
    email: str | None = None
    custom_fields: dict[str, Any] | None = None
    opt_in: bool | None = None
    status: str | None = None
    tag_ids: list[int] | None = None


class ContactResponse(BaseModel):
    """Contato na resposta (com tags e list_ids)."""
    id: int
    tenant_id: int
    phone: str
    name: str | None
    email: str | None
    custom_fields: dict
    opt_in: bool
    status: str
    tags: list[str] = Field(default_factory=list)
    list_ids: list[int] = Field(default_factory=list)
    created_at: datetime | None
    updated_at: datetime | None
    last_sent_at: datetime | None
    last_response_at: datetime | None

    class Config:
        from_attributes = True


# --- Sync (API para sistemas externos) ---


class ContactSyncItem(BaseModel):
    """Um item do payload de sync."""
    phone: str = Field(..., min_length=1, max_length=20)
    name: str | None = None
    email: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    list_id: int | None = None
    opt_in: bool = True


class ContactSyncBody(BaseModel):
    """Body do POST /contacts/sync."""
    contacts: list[ContactSyncItem] = Field(..., max_length=5000)


class ContactSyncResponse(BaseModel):
    """Resposta do sync."""
    created: int = 0
    updated: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ContactBulkDeleteBody(BaseModel):
    """Body para exclusão em lote de contatos."""
    ids: list[int] = Field(default_factory=list, min_length=1)


class ContactBulkDeleteResponse(BaseModel):
    """Resultado da exclusão em lote de contatos."""
    deleted: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)
