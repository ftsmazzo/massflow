"""
Instâncias Evolution API: CRUD e conexão (QR).
Respeita plano do tenant: 1=só minhas, 2=só plataforma, 3=ambas.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant, PlanType
from app.models.evolution_instance import EvolutionInstance
from app.config import settings
from app.schemas.evolution_instance import (
    InstanceCreate,
    InstanceUpdate,
    InstanceResponse,
    InstanceConnectResponse,
    SyncInboundWebhookBody,
    SyncInboundWebhookResponse,
    SyncInboundWebhookResultItem,
    InboundWebhookStatusItem,
    InboundWebhookStatusResponse,
)
from app.services.evolution import (
    create_instance as evo_create,
    connect_instance,
    fetch_connection_state,
    disconnect_instance as evo_disconnect,
    find_webhook_sync,
    set_webhook_sync,
)

router = APIRouter(prefix="/instances", tags=["Instances"])


def _can_use_tenant_instances(tenant: Tenant) -> bool:
    """Plano 1 ou 3: pode usar instâncias próprias (owner=tenant)."""
    return tenant.plan_type in (PlanType.OWN_ONLY, PlanType.HYBRID)


def _can_use_platform_instances(tenant: Tenant) -> bool:
    """Plano 2 ou 3: pode usar instâncias da plataforma."""
    return tenant.plan_type in (PlanType.PLATFORM_ONLY, PlanType.HYBRID)


def _can_create_tenant_instance(tenant: Tenant) -> bool:
    """Pode cadastrar instância própria (owner=tenant)."""
    return _can_use_tenant_instances(tenant)


@router.get("", response_model=list[InstanceResponse])
def list_instances(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    owner: str | None = Query(None, description="Filtrar: tenant | platform"),
):
    """Lista instâncias disponíveis para o tenant (respeitando plano)."""
    tenant = user.tenant
    q = db.query(EvolutionInstance)
    if _can_use_tenant_instances(tenant) and _can_use_platform_instances(tenant):
        if owner == "tenant":
            q = q.filter(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.owner == "tenant")
        elif owner == "platform":
            q = q.filter(EvolutionInstance.owner == "platform")
        else:
            q = q.filter(
                or_(
                    and_(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.owner == "tenant"),
                    EvolutionInstance.owner == "platform",
                )
            )
    elif _can_use_tenant_instances(tenant):
        q = q.filter(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.owner == "tenant")
    elif _can_use_platform_instances(tenant):
        q = q.filter(EvolutionInstance.owner == "platform")
    else:
        return []
    return q.all()


def _instances_for_user(user: User, db: Session) -> list[EvolutionInstance]:
    """Mesmas regras de listagem de instâncias (tenant + plataforma conforme plano)."""
    tenant = user.tenant
    q = db.query(EvolutionInstance)
    if _can_use_tenant_instances(tenant) and _can_use_platform_instances(tenant):
        q = q.filter(
            or_(
                and_(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.owner == "tenant"),
                EvolutionInstance.owner == "platform",
            )
        )
    elif _can_use_tenant_instances(tenant):
        q = q.filter(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.owner == "tenant")
    elif _can_use_platform_instances(tenant):
        q = q.filter(EvolutionInstance.owner == "platform")
    else:
        return []
    return q.all()


def _resolve_public_api_base(request: Request, body: SyncInboundWebhookBody) -> str:
    if body.public_api_base and str(body.public_api_base).strip():
        return str(body.public_api_base).strip().rstrip("/")
    pub = (settings.PUBLIC_BASE_URL or "").strip()
    if pub:
        return pub.rstrip("/")
    return str(request.base_url).rstrip("/")


@router.post("/sync-inbound-webhook", response_model=SyncInboundWebhookResponse)
def sync_inbound_webhook(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    body: SyncInboundWebhookBody = SyncInboundWebhookBody(),
):
    """
    Configura na Evolution API o webhook de mensagens recebidas para **todas** as instâncias do tenant.
    Uma única URL no MassFlow; o corpo do POST da Evolution identifica qual número (`instance`).
    """
    tenant_id = user.tenant_id
    public_base = _resolve_public_api_base(request, body)
    webhook_url = f"{public_base}/api/campaigns/inbound/{tenant_id}"
    instances = _instances_for_user(user, db)
    if not instances:
        raise HTTPException(status_code=400, detail="Nenhuma instância disponível.")
    results: list[SyncInboundWebhookResultItem] = []
    for inst in instances:
        try:
            set_webhook_sync(inst.api_url, inst.api_key or "", inst.name, webhook_url)
            results.append(
                SyncInboundWebhookResultItem(instance_id=inst.id, name=inst.name, ok=True, detail=None)
            )
        except Exception as e:
            results.append(
                SyncInboundWebhookResultItem(
                    instance_id=inst.id,
                    name=inst.name,
                    ok=False,
                    detail=str(e)[:400],
                )
            )
    return SyncInboundWebhookResponse(tenant_id=tenant_id, webhook_url=webhook_url, results=results)


def _normalize_url_for_compare(u: str) -> str:
    s = (u or "").strip().rstrip("/")
    if s.startswith("https://https://"):
        s = "https://" + s[16:]
    elif s.startswith("http://http://"):
        s = "http://" + s[13:]
    return s.lower()


def _extract_evolution_webhook_url_and_events(data: dict) -> tuple[str | None, list[str] | None, bool | None]:
    """Resposta plana ou aninhada (webhook.webhook)."""
    if not isinstance(data, dict):
        return None, None, None
    url = data.get("url")
    events = data.get("events")
    enabled = data.get("enabled")
    inner = data.get("webhook")
    if isinstance(inner, dict):
        if url is None:
            url = inner.get("url")
        if events is None:
            events = inner.get("events")
        if enabled is None:
            enabled = inner.get("enabled")
        nested = inner.get("webhook")
        if isinstance(nested, dict):
            if url is None:
                url = nested.get("url")
            if events is None:
                events = nested.get("events")
            if enabled is None:
                enabled = nested.get("enabled")
    ev_list: list[str] | None = None
    if isinstance(events, list):
        ev_list = [str(e) for e in events]
    en_bool = enabled if isinstance(enabled, bool) else None
    return (str(url).strip() if url else None), ev_list, en_bool


@router.get("/inbound-webhook-status", response_model=InboundWebhookStatusResponse)
def inbound_webhook_status(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    public_api_base: str | None = Query(
        None,
        description="Mesma base pública usada no sync (ou PUBLIC_BASE_URL); se vazio, deduz do pedido.",
    ),
):
    """
    Lê na Evolution (`GET /webhook/find/{instance}`) o que está configurado e compara com a URL
    que o MassFlow espera para inbound. Use para provar se o problema é URL errada ou Evolution não chamando.
    """
    tenant_id = user.tenant_id
    body = SyncInboundWebhookBody(public_api_base=public_api_base)
    public_base = _resolve_public_api_base(request, body)
    expected = f"{public_base}/api/campaigns/inbound/{tenant_id}"
    expected_n = _normalize_url_for_compare(expected)
    instances = _instances_for_user(user, db)
    out: list[InboundWebhookStatusItem] = []
    for inst in instances:
        try:
            raw = find_webhook_sync(inst.api_url, inst.api_key or "", inst.name)
            ev_url, ev_events, ev_en = _extract_evolution_webhook_url_and_events(raw)
            match = (
                _normalize_url_for_compare(ev_url or "") == expected_n
                if ev_url
                else None
            )
            out.append(
                InboundWebhookStatusItem(
                    instance_id=inst.id,
                    name=inst.name,
                    ok=True,
                    detail=None,
                    evolution_url=ev_url,
                    evolution_events=ev_events,
                    evolution_enabled=ev_en,
                    url_matches_expected=match,
                )
            )
        except Exception as e:
            out.append(
                InboundWebhookStatusItem(
                    instance_id=inst.id,
                    name=inst.name,
                    ok=False,
                    detail=str(e)[:500],
                    evolution_url=None,
                    evolution_events=None,
                    evolution_enabled=None,
                    url_matches_expected=None,
                )
            )
    return InboundWebhookStatusResponse(
        tenant_id=tenant_id,
        expected_inbound_url=expected,
        instances=out,
    )


@router.post("", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    body: InstanceCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Cadastra e cria uma instância na Evolution API (owner=tenant). Plano 1 ou 3."""
    tenant = user.tenant
    if not _can_create_tenant_instance(tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu plano não permite cadastrar instâncias próprias. Use instâncias da plataforma.",
        )
    existing = db.query(EvolutionInstance).filter(
        EvolutionInstance.tenant_id == tenant.id,
        EvolutionInstance.name == body.name,
        EvolutionInstance.owner == "tenant",
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Já existe uma instância com este nome.")
    try:
        evo_create_result = await evo_create(body.api_url, body.api_key, body.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution API: {str(e)}")
    instance = EvolutionInstance(
        tenant_id=tenant.id,
        name=body.name,
        api_url=body.api_url,
        api_key=body.api_key or (evo_create_result.get("hash", {}).get("apikey") or ""),
        display_name=body.display_name or body.name,
        owner="tenant",
        status=evo_create_result.get("instance", {}).get("status") or "created",
        limits={},
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@router.get("/{instance_id}", response_model=InstanceResponse)
def get_instance(
    instance_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retorna uma instância (se o tenant tiver acesso)."""
    tenant = user.tenant
    inst = db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "tenant" and inst.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "platform" and not _can_use_platform_instances(tenant):
        raise HTTPException(status_code=403, detail="Sem acesso a esta instância.")
    return inst


@router.patch("/{instance_id}", response_model=InstanceResponse)
def update_instance(
    instance_id: int,
    body: InstanceUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Atualiza display_name, api_url, api_key ou limits (apenas instâncias próprias)."""
    tenant = user.tenant
    inst = db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
    if not inst or inst.tenant_id != tenant.id or inst.owner != "tenant":
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if body.display_name is not None:
        inst.display_name = body.display_name
    if body.api_url is not None:
        inst.api_url = body.api_url
    if body.api_key is not None:
        inst.api_key = body.api_key
    if body.limits is not None:
        inst.limits = body.limits
    db.commit()
    db.refresh(inst)
    return inst


@router.post("/{instance_id}/connect", response_model=InstanceConnectResponse)
async def instance_connect(
    instance_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Gera QR code / pairing code para conectar a instância ao WhatsApp."""
    tenant = user.tenant
    inst = db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "tenant" and inst.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "platform" and not _can_use_platform_instances(tenant):
        raise HTTPException(status_code=403, detail="Sem acesso.")
    try:
        data = await connect_instance(inst.api_url, inst.api_key, inst.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution API: {str(e)}")
    return InstanceConnectResponse(
        pairing_code=data.get("pairingCode"),
        code=data.get("code"),
        count=data.get("count"),
    )


@router.get("/{instance_id}/status")
async def instance_status(
    instance_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Consulta estado da conexão na Evolution API."""
    tenant = user.tenant
    inst = db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
    if not inst or (inst.owner == "tenant" and inst.tenant_id != tenant.id):
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "platform" and not _can_use_platform_instances(tenant):
        raise HTTPException(status_code=403, detail="Sem acesso.")
    state = await fetch_connection_state(inst.api_url, inst.api_key, inst.name)
    return {"instance": inst.name, "connection_state": state}


def _raw_connection_state_label(state: dict | None) -> str:
    """
    Evolution 2.x costuma devolver o estado em `instance.state` (doc), não no topo.
    Aceita também formato plano (`state` / `status` na raiz).
    """
    if not state or not isinstance(state, dict):
        return ""
    for key in ("state", "status", "connectionStatus"):
        v = state.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    inner = state.get("instance")
    if isinstance(inner, dict):
        for key in ("state", "status", "connectionStatus"):
            v = inner.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _state_to_status(state: dict | None) -> str:
    """Mapeia connection_state da Evolution para status local (connected, close, etc.)."""
    if not state:
        return "close"
    s = _raw_connection_state_label(state).lower()
    if s in ("open", "connected"):
        return "connected"
    return s or "close"


@router.post("/{instance_id}/refresh", response_model=InstanceResponse)
async def instance_refresh(
    instance_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Atualiza status (e opcionalmente phone) da instância consultando a Evolution API."""
    tenant = user.tenant
    inst = db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
    if not inst or (inst.owner == "tenant" and inst.tenant_id != tenant.id):
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "platform" and not _can_use_platform_instances(tenant):
        raise HTTPException(status_code=403, detail="Sem acesso.")
    try:
        state = await fetch_connection_state(inst.api_url, inst.api_key, inst.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution API: {str(e)}")
    inst.status = _state_to_status(state)
    # Evolution pode retornar instance?.owner no state; phone pode vir em outro campo
    if state and not inst.phone_number:
        owner = state.get("instance", {}).get("owner") or state.get("owner")
        if isinstance(owner, str) and owner.isdigit():
            inst.phone_number = owner
    db.commit()
    db.refresh(inst)
    return inst


@router.post("/{instance_id}/disconnect", response_model=InstanceResponse)
async def instance_disconnect(
    instance_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Desconecta a instância do WhatsApp (Evolution API logout) e atualiza status no banco."""
    tenant = user.tenant
    inst = db.query(EvolutionInstance).filter(EvolutionInstance.id == instance_id).first()
    if not inst or (inst.owner == "tenant" and inst.tenant_id != tenant.id):
        raise HTTPException(status_code=404, detail="Instância não encontrada.")
    if inst.owner == "platform" and not _can_use_platform_instances(tenant):
        raise HTTPException(status_code=403, detail="Sem acesso.")
    try:
        await evo_disconnect(inst.api_url, inst.api_key, inst.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Evolution API: {str(e)}")
    inst.status = "close"
    db.commit()
    db.refresh(inst)
    return inst
