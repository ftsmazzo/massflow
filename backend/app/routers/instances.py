"""
Instâncias Evolution API: CRUD e conexão (QR).
Respeita plano do tenant: 1=só minhas, 2=só plataforma, 3=ambas.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant, PlanType
from app.models.evolution_instance import EvolutionInstance
from app.schemas.evolution_instance import (
    InstanceCreate,
    InstanceUpdate,
    InstanceResponse,
    InstanceConnectResponse,
)
from app.services.evolution import create_instance as evo_create, connect_instance, fetch_connection_state

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
