"""
Configuração global de blindagem (por tenant).
GET retorna config com defaults; PUT salva.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.shielding_config import TenantShieldingConfig
from app.schemas.shielding import (
    ShieldingConfigBody,
    default_config_dict,
    config_from_dict,
)

router = APIRouter(prefix="/settings/shielding", tags=["Shielding"])


@router.get("", response_model=ShieldingConfigBody)
def get_shielding_config(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retorna a configuração global de blindagem do tenant (com defaults se ainda não existir)."""
    tenant_id = user.tenant_id
    row = db.query(TenantShieldingConfig).filter(TenantShieldingConfig.tenant_id == tenant_id).first()
    if not row or not row.config:
        return config_from_dict(default_config_dict())
    return config_from_dict(row.config)


@router.put("", response_model=ShieldingConfigBody)
def put_shielding_config(
    body: ShieldingConfigBody,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Salva a configuração global de blindagem do tenant."""
    tenant_id = user.tenant_id
    row = db.query(TenantShieldingConfig).filter(TenantShieldingConfig.tenant_id == tenant_id).first()
    data = body.model_dump()
    if not row:
        row = TenantShieldingConfig(tenant_id=tenant_id, config=data)
        db.add(row)
    else:
        row.config = data
    db.commit()
    db.refresh(row)
    return config_from_dict(row.config)
