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
