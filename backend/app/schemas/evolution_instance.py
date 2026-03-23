"""
Schemas para EvolutionInstance
"""
from pydantic import BaseModel, Field
from typing import Any


class InstanceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    api_url: str = Field(..., min_length=1, max_length=500)
    api_key: str = ""
    display_name: str | None = None


class InstanceUpdate(BaseModel):
    display_name: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    limits: dict[str, Any] | None = None


class InstanceResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    api_url: str
    display_name: str | None
    owner: str
    status: str
    phone_number: str | None = None
    limits: dict
    created_at: Any

    class Config:
        from_attributes = True


class InstanceConnectResponse(BaseModel):
    pairing_code: str | None = None
    code: str | None = None
    count: int | None = None


class SyncInboundWebhookBody(BaseModel):
    """URL pública do MassFlow (sem path /api). Se vazio, usa PUBLIC_BASE_URL ou o host do pedido."""
    public_api_base: str | None = None


class SyncInboundWebhookResultItem(BaseModel):
    instance_id: int
    name: str
    ok: bool
    detail: str | None = None


class SyncInboundWebhookResponse(BaseModel):
    tenant_id: int
    webhook_url: str
    results: list[SyncInboundWebhookResultItem]


class InboundWebhookStatusItem(BaseModel):
    instance_id: int
    name: str
    ok: bool
    detail: str | None = None
    evolution_url: str | None = None
    evolution_events: list[str] | None = None
    evolution_enabled: bool | None = None
    url_matches_expected: bool | None = None


class InboundWebhookStatusResponse(BaseModel):
    tenant_id: int
    expected_inbound_url: str
    instances: list[InboundWebhookStatusItem]
