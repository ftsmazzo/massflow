"""
Schemas para Tags (funis e segmentação).
"""
from datetime import datetime

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    """Criação de tag."""
    name: str = Field(..., min_length=1, max_length=100)


class TagUpdate(BaseModel):
    """Atualização de tag (nome)."""
    name: str = Field(..., min_length=1, max_length=100)


class TagResponse(BaseModel):
    """Tag na resposta."""
    id: int
    tenant_id: int
    name: str
    created_at: datetime | None

    class Config:
        from_attributes = True


class TagApplyBody(BaseModel):
    """Body para aplicar tag a contatos."""
    contact_ids: list[int] = Field(..., min_length=1, max_length=500)
