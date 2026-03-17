"""
Schemas para Listas (agrupamento de contatos).
"""
from datetime import datetime

from pydantic import BaseModel, Field


class ListCreate(BaseModel):
    """Criação de lista."""
    name: str = Field(..., min_length=1, max_length=255)


class ListUpdate(BaseModel):
    """Atualização parcial de lista."""
    name: str | None = Field(None, min_length=1, max_length=255)


class ListResponse(BaseModel):
    """Lista na resposta."""
    id: int
    tenant_id: int
    name: str
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True


class ListWithContactsResponse(ListResponse):
    """Lista com contagem de contatos (ou IDs)."""
    contact_count: int = 0


class ListAddContactsBody(BaseModel):
    """Body para adicionar contatos à lista."""
    contact_ids: list[int] = Field(..., min_length=1, max_length=500)


class ListRemoveContactsBody(BaseModel):
    """Body para remover contatos da lista."""
    contact_ids: list[int] = Field(..., min_length=1, max_length=500)
