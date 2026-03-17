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

    # Redis (filas / cache)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    @property
    def cors_origins_list(self) -> List[str]:
        origins = []
        for o in self.CORS_ORIGINS.split(","):
            o = o.strip()
            if not o:
                continue
            # Corrige duplicação comum: "https://https://dominio" -> "https://dominio"
            if o.startswith("https://https://"):
                o = "https://" + o[16:]
            elif o.startswith("http://http://"):
                o = "http://" + o[13:]
            origins.append(o)
        return origins

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
