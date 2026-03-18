"""
Schemas para Campanhas.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class CampaignContent(BaseModel):
    """Conteúdo da campanha (texto, mídia, variáveis)."""
    type: str = Field("text", description="text | image | video | audio | document")
    text: str | None = Field(None, description="Texto com variáveis {nome}, spintax, etc.")
    media_url: str | None = Field(None, description="URL da mídia (imagem, vídeo, áudio, documento)")
    caption: str | None = Field(None, description="Legenda quando type é image/video/document")


class CampaignCreate(BaseModel):
    """Criação de campanha."""
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field("immediate", pattern="^(immediate|scheduled)$")
    list_id: int = Field(..., gt=0)
    tag_filter_include: list[str] | None = Field(None, max_length=50)
    tag_filter_exclude: list[str] | None = Field(None, max_length=50)
    content: dict = Field(default_factory=dict, description="type, text, media_url, caption")
    use_global_shielding: bool = True
    shielding_override: dict | None = None
    instance_ids: list[int] | None = Field(None, description="null = todas as instâncias")
    scheduled_at: datetime | None = None


class CampaignUpdate(BaseModel):
    """Atualização parcial de campanha (draft)."""
    name: str | None = Field(None, min_length=1, max_length=255)
    type: str | None = Field(None, pattern="^(immediate|scheduled)$")
    list_id: int | None = Field(None, gt=0)
    tag_filter_include: list[str] | None = None
    tag_filter_exclude: list[str] | None = None
    content: dict | None = None
    use_global_shielding: bool | None = None
    shielding_override: dict | None = None
    instance_ids: list[int] | None = None
    scheduled_at: datetime | None = None


class CampaignResponse(BaseModel):
    """Campanha na resposta."""
    id: int
    tenant_id: int
    name: str
    type: str
    list_id: int
    tag_filter_include: list[str] | None
    tag_filter_exclude: list[str] | None
    content: dict
    use_global_shielding: bool
    shielding_override: dict | None
    instance_ids: list[int] | None
    status: str
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime | None
    updated_at: datetime | None

    class Config:
        from_attributes = True
