"""
Auth: registro (cria tenant + primeiro usuário), login, me
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, verify_password, create_access_token
from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.auth import RegisterRequest, LoginRequest, Token, UserResponse
from app.schemas.tenant import TenantResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


def slugify(name: str) -> str:
    """Gera slug a partir do nome (ex: 'Minha Empresa' -> 'minha-empresa')."""
    s = name.lower().strip()
    for c in " \t":
        s = s.replace(c, "-")
    return "".join(c for c in s if c.isalnum() or c == "-").strip("-") or "tenant"


@router.post("/register", response_model=Token)
def register(
    body: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Cria um novo tenant e o primeiro usuário (admin). Retorna token JWT."""
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado",
        )
    slug = slugify(body.tenant_name)
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        # Garante slug único
        slug = f"{slug}-{db.query(Tenant).count() + 1}"
    tenant = Tenant(
        name=body.tenant_name,
        slug=slug,
        plan_type=1,
        credits_balance=0,
        active=True,
    )
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name or body.email.split("@")[0],
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, extra_claims={"tenant_id": tenant.id})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Login por e-mail e senha. Retorna token JWT."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário inativo")
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token(user.id, extra_claims={"tenant_id": user.tenant_id})
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: Annotated[User, Depends(get_current_user)]):
    """Retorna o usuário autenticado."""
    return user
