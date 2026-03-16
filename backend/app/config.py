"""
Configurações do MassFlow (Pydantic Settings + .env)
"""
import os
from pydantic_settings import BaseSettings
from typing import List

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/massflow"
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "10080")
    )  # 7 dias

    # CORS
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    )

    # Evolution API (base - instâncias por tenant no DB)
    EVOLUTION_API_URL: str = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
    EVOLUTION_API_KEY: str = os.getenv("EVOLUTION_API_KEY", "")

    # Agentes SaaS (integração assinatura/créditos) - opcional
    AGENTES_SAAS_API_URL: str = os.getenv("AGENTES_SAAS_API_URL", "")
    AGENTES_SAAS_API_KEY: str = os.getenv("AGENTES_SAAS_API_KEY", "")

    # Redis (opcional - filas)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
