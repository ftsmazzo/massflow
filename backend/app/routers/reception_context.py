"""
Gravação do contexto de recepção (n8n) após gerar a mensagem — chamada via HTTP com segredo compartilhado.
"""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.reception_context import ReceptionContext
from app.models.tenant import Tenant
from app.schemas.reception_context import ReceptionContextCreate

router = APIRouter(prefix="/reception-context", tags=["Reception context"])


def _require_reception_secret(request: Request) -> None:
    expected = (settings.RECEPTION_CONTEXT_SECRET or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Endpoint desativado: defina RECEPTION_CONTEXT_SECRET no ambiente do backend.",
        )
    header_secret = (request.headers.get("X-Massflow-Reception-Secret") or "").strip()
    auth = (request.headers.get("Authorization") or "").strip()
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if header_secret == expected or bearer == expected:
        return
    raise HTTPException(status_code=401, detail="Credencial inválida ou ausente.")


@router.post("", status_code=201)
async def create_reception_context(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Insere uma linha em `reception_contexts`. Use no n8n após o nó que gera `msg_recepcao`.

    Autenticação: header `X-Massflow-Reception-Secret: <RECEPTION_CONTEXT_SECRET>`
    ou `Authorization: Bearer <RECEPTION_CONTEXT_SECRET>`.

    Body: JSON objeto. Se o n8n enviar `[{ ... }]`, também é aceito (um único elemento).
    """
    _require_reception_secret(request)
    raw_bytes = await request.body()
    if not raw_bytes or not raw_bytes.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Body JSON ausente. No n8n (HTTP Request): POST, em Body escolha JSON e "
                "garanta que a expressão retorne um objeto { }, não só campos soltos. "
                "Se usar expressão, prefira retorno direto do objeto (sem colocar o item dentro de array)."
            ),
        )
    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=422, detail=f"JSON inválido: {e!s}") from e

    if isinstance(data, list):
        if len(data) != 1:
            raise HTTPException(
                status_code=422,
                detail="Se enviar array, use exatamente um objeto: [{ ... }].",
            )
        data = data[0]
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=422,
            detail="O body deve ser um objeto JSON (ou array com um objeto).",
        )

    try:
        body = ReceptionContextCreate.model_validate(data)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors()) from e

    tenant = db.query(Tenant).filter(Tenant.id == body.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="tenant_id não encontrado.")

    if body.lead_id is not None:
        lead = (
            db.query(Lead)
            .filter(Lead.id == body.lead_id, Lead.tenant_id == body.tenant_id)
            .first()
        )
        if not lead:
            raise HTTPException(status_code=400, detail="lead_id não pertence ao tenant.")

    if body.campaign_id is not None:
        camp = (
            db.query(Campaign)
            .filter(Campaign.id == body.campaign_id, Campaign.tenant_id == body.tenant_id)
            .first()
        )
        if not camp:
            raise HTTPException(status_code=400, detail="campaign_id não pertence ao tenant.")

    mensagem_lead = body.lead_message or body.mensagem_lead
    campanha = body.campaign_name or body.campanha
    msg_campanha = body.campaign_outbound_message or body.msg_campanha

    phone = "".join(c for c in body.lead_phone if c.isdigit()) or body.lead_phone.strip()

    payload = {
        "lead_name": body.lead_name,
        "lead_phone": phone,
        "mensagem_lead": mensagem_lead,
        "campanha": campanha,
        "msg_campanha": msg_campanha,
        "msg_recepcao": body.msg_recepcao.strip(),
    }

    campanha_col = None
    if campanha is not None:
        campanha_col = campanha[:255] if len(campanha) > 255 else campanha

    row = ReceptionContext(
        tenant_id=body.tenant_id,
        lead_id=body.lead_id,
        campaign_id=body.campaign_id,
        lead_phone=phone,
        lead_name=body.lead_name,
        mensagem_lead=mensagem_lead,
        campanha=campanha_col,
        msg_campanha=msg_campanha,
        msg_recepcao=body.msg_recepcao.strip(),
        payload=payload,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "created": True}
