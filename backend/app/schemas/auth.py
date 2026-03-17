"""
Schemas para registro, login e usuário autenticado
"""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None
    tenant_name: str  # Nome da organização (cria tenant + primeiro usuário admin)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None
    tenant_id: int
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True
