"""
Payload para gravar contexto de recepção (n8n → MassFlow).
"""
from pydantic import BaseModel, Field


class ReceptionContextCreate(BaseModel):
    """Campos do webhook de campanha + mensagem gerada pelo fluxo (LLM)."""

    msg_recepcao: str = Field(..., min_length=1, description="Texto final gerado no n8n.")
    tenant_id: int = Field(..., ge=1)
    lead_phone: str = Field(..., min_length=3, max_length=30)

    lead_id: int | None = None
    campaign_id: int | None = None
    lead_name: str | None = None

    lead_message: str | None = None
    mensagem_lead: str | None = None

    campaign_name: str | None = None
    campanha: str | None = None

    campaign_outbound_message: str | None = None
    msg_campanha: str | None = None
