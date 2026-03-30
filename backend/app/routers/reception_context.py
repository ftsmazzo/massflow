"""
Gravação do contexto de recepção (n8n) após gerar a mensagem — chamada via HTTP com segredo compartilhado.
"""
import json
from datetime import datetime
from typing import Annotated, Any
from urllib.parse import parse_qs

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.campaign_qualification import CampaignQualificationConfig
from app.models.reception_context import ReceptionContext
from app.models.tenant import Tenant
from app.schemas.reception_context import ReceptionContextCreate
from app.services.campaign_resolution import (
    mark_latest_inbound_agent_context_consumed,
    resolve_campaign_id_for_qualification,
)
from app.services.inbound_evolution import normalize_phone_digits, phones_match_for_lead
from app.services.reconciliation_trigger import attach_reconcile_jobs_after_context_consumed

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


def _form_value_to_primitive(value: Any) -> Any:
    if hasattr(value, "read"):
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _dict_from_starlette_form(form: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in form.multi_items():
        v = _form_value_to_primitive(value)
        if v is None:
            continue
        out[key] = v
    return out


def _normalize_ids_for_schema(data: dict[str, Any]) -> dict[str, Any]:
    """Form envia strings; ids opcionais vazios são removidos."""
    out = dict(data)
    for k in ("lead_id", "campaign_id"):
        if k not in out:
            continue
        val = out[k]
        if val is None or (isinstance(val, str) and not val.strip()):
            del out[k]
            continue
        if isinstance(val, str):
            try:
                out[k] = int(val.strip())
            except ValueError:
                del out[k]
        elif isinstance(val, int):
            pass
        else:
            try:
                out[k] = int(val)
            except (TypeError, ValueError):
                del out[k]
    if "tenant_id" in out and isinstance(out["tenant_id"], str):
        out["tenant_id"] = int(out["tenant_id"].strip())
    return out


def _parse_body_to_dict(raw_bytes: bytes) -> dict[str, Any]:
    if not raw_bytes or not raw_bytes.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Corpo vazio. No n8n (HTTP Request v4): (A) Body → Content Type "
                "'Form-Urlencoded' → Add Parameter: msg_recepcao, tenant_id, lead_phone "
                "(e opcionais lead_id, campaign_id, lead_name, lead_message, campaign_name, "
                "campaign_outbound_message). "
                "(B) Ou Body → JSON → expressão exatamente: ={{ JSON.stringify($json) }} "
                "(com '=' no início). "
                "(C) Ou nó Code antes do HTTP: return { json: { ... } }. "
                "Na execução, abra a aba que mostra o request e confira se há body."
            ),
        )
    text = raw_bytes.decode("utf-8").strip()
    if text.startswith("{") or text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"JSON inválido: {e!s}") from e
        if isinstance(parsed, list):
            if len(parsed) != 1:
                raise HTTPException(
                    status_code=422,
                    detail="Se enviar array, use exatamente um objeto: [{ ... }].",
                )
            parsed = parsed[0]
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=422, detail="JSON deve ser um objeto na raiz.")
        return parsed
    qs = parse_qs(text, keep_blank_values=True)
    if not qs:
        raise HTTPException(
            status_code=422,
            detail="Body não é JSON. Use Form-Urlencoded no n8n ou JSON com objeto { ... }.",
        )
    flat = {k: (vals[0] if len(vals) == 1 else vals) for k, vals in qs.items()}
    return _normalize_ids_for_schema(flat)


def _build_agent_first_instruction(row: ReceptionContext) -> str:
    lead_name = (row.lead_name or "Contato").strip()
    phone = (row.lead_phone or "").strip()
    campanha = (row.campanha or "campanha não informada").strip()
    msg_campanha = (row.msg_campanha or "").strip() or "mensagem da campanha não registrada"
    mensagem_lead = (row.mensagem_lead or "").strip() or "resposta inicial não registrada"
    msg_recepcao = (row.msg_recepcao or "").strip() or "mensagem de recepção não registrada"
    return (
        "Instrução de contexto para PRIMEIRA interação deste atendimento:\n"
        f"- Lead: {lead_name}\n"
        f"- Telefone: {phone}\n"
        f"- Origem: respondeu ao disparo da campanha \"{campanha}\".\n"
        f"- Mensagem recebida na campanha: {msg_campanha}\n"
        f"- Resposta inicial do lead: {mensagem_lead}\n"
        f"- Mensagem de recepção já enviada: {msg_recepcao}\n"
        "Agora continue a conversa a partir deste ponto, sem repetir a mensagem de recepção."
    )


@router.post("", status_code=201)
async def create_reception_context(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Insere uma linha em `reception_contexts`. Use no n8n após o nó que gera `msg_recepcao`.

    Autenticação: header `X-Massflow-Reception-Secret: <RECEPTION_CONTEXT_SECRET>`
    ou `Authorization: Bearer <RECEPTION_CONTEXT_SECRET>`.

    Body: JSON objeto ou `[{ ... }]`; ou **Form-Urlencoded** / **multipart** com os mesmos campos
    (recomendado se o JSON do n8n estiver indo vazio).
    """
    _require_reception_secret(request)
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()

    if content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
        form = await request.form()
        data = _normalize_ids_for_schema(_dict_from_starlette_form(form))
    else:
        raw_bytes = await request.body()
        data = _normalize_ids_for_schema(_parse_body_to_dict(raw_bytes))

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


@router.get("/next-first-interaction")
def consume_next_first_interaction_context(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    tenant_id: int,
    lead_phone: str,
    consume: bool = True,
):
    """
    Busca o último reception_context não consumido para tenant+telefone.
    Se `consume=true`, marca consumed_at=now() ao devolver.
    """
    _require_reception_secret(request)
    phone = normalize_phone_digits(str(lead_phone or ""))
    if not phone:
        raise HTTPException(status_code=422, detail="lead_phone inválido.")

    # Mesma tolerância do inbound (55 vs DDD, sufixos): evita found=false por formato diferente.
    candidates = (
        db.query(ReceptionContext)
        .filter(
            ReceptionContext.tenant_id == tenant_id,
            ReceptionContext.consumed_at.is_(None),
        )
        .order_by(ReceptionContext.created_at.desc(), ReceptionContext.id.desc())
        .limit(80)
        .all()
    )
    row = next((r for r in candidates if phones_match_for_lead(phone, r.lead_phone)), None)
    if not row:
        return {"found": False, "instruction": None}

    instruction = _build_agent_first_instruction(row)
    reconcile_meta: dict = {}
    campaign_resolved = resolve_campaign_id_for_qualification(
        db,
        tenant_id=tenant_id,
        lead_phone=phone,
        lead_id=row.lead_id,
        reception_campaign_id=row.campaign_id,
    )
    inbound_marked = False
    if consume:
        row.consumed_at = datetime.utcnow()
        db.commit()
        # Sinal em campaign_inbound_replies: agente consumiu o contexto da 1ª interação.
        if campaign_resolved is not None:
            inbound_marked = mark_latest_inbound_agent_context_consumed(
                db,
                tenant_id=tenant_id,
                campaign_id=campaign_resolved,
                lead_phone=phone,
                lead_id=row.lead_id,
            )
        # Reconciliação SaaS → qualificação: campanha vem do contexto OU do último inbound (disparo atual).
        if campaign_resolved is not None:
            cfg = (
                db.query(CampaignQualificationConfig)
                .filter(
                    CampaignQualificationConfig.tenant_id == tenant_id,
                    CampaignQualificationConfig.campaign_id == campaign_resolved,
                )
                .first()
            )
            if cfg and getattr(cfg, "reconcile_from_saas_chat", False):
                reconcile_meta = attach_reconcile_jobs_after_context_consumed(
                    background_tasks,
                    tenant_id=tenant_id,
                    campaign_id=campaign_resolved,
                    lead_phone=phone,
                    lead_id=row.lead_id,
                    lead_name=row.lead_name,
                )

    out = {
        "found": True,
        "reception_context_id": row.id,
        "instruction": instruction,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "consumed_at": row.consumed_at.isoformat() if row.consumed_at else None,
        "campaign_id_resolved": campaign_resolved,
        "agent_context_inbound_marked": inbound_marked,
    }
    out.update(reconcile_meta)
    return out
