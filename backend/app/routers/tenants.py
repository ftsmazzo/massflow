"""
Tenant: dados da organização do usuário autenticado (multi-tenant)
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models.user import User
from app.schemas.tenant import TenantResponse

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/me", response_model=TenantResponse)
def get_my_tenant(user: Annotated[User, Depends(get_current_user)]):
    """Retorna o tenant do usuário autenticado."""
    return user.tenant
