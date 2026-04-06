"""
Schemas para Tags (funis e segmentação).
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


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


class TagBulkUpdateBody(BaseModel):
    """
    Operação em massa: escopo (lista e/ou IDs) + filtros por tags + adicionar/remover tags.

    Ex.: lista \"Super endividamento\", deve ter tag base, sem nenhuma \"disparo 2\",
    adicionar \"disparo 3\".
    """

    list_id: int | None = None
    contact_ids: list[int] | None = Field(None, max_length=5000)
    require_all_tag_ids: list[int] = Field(default_factory=list, max_length=20)
    without_any_tag_ids: list[int] = Field(default_factory=list, max_length=20)
    add_tag_ids: list[int] = Field(default_factory=list, max_length=20)
    remove_tag_ids: list[int] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def _validate_scope_and_ops(self) -> Any:
        if self.list_id is None and not self.contact_ids:
            raise ValueError("Informe list_id (contatos da lista) e/ou contact_ids.")
        if not self.add_tag_ids and not self.remove_tag_ids:
            raise ValueError("Informe add_tag_ids e/ou remove_tag_ids.")
        return self


class TagBulkUpdateResponse(BaseModel):
    matched_leads: int
    tags_added_links: int
    tags_removed_links: int
    capped: bool = False
