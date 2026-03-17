"""
Modelo Tenant (organização / conta do cliente)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
import enum

from app.database import Base


class PlanType(int, enum.Enum):
    """Nível da conta: 1=só minhas instâncias, 2=só plataforma, 3=ambas"""
    OWN_ONLY = 1
    PLATFORM_ONLY = 2
    HYBRID = 3


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # Plano: 1, 2 ou 3 (ver PlanType)
    plan_type = Column(Integer, default=1, nullable=False)
    credits_balance = Column(Integer, default=0)  # Créditos avulsos para disparos

    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relações (evitar circular import - declarar nos outros modelos)
    # users = relationship("User", back_populates="tenant")
