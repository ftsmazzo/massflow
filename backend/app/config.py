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

    # Opcional: Postgres externo (ex.: tabela chatMessages do SaaS) para reconciliação de qualificação.
    # Vazio = funcionalidade não usa segundo banco (implementação do job pode checar isso).
    SAAS_CHAT_HISTORY_DATABASE_URL: str = os.getenv("SAAS_CHAT_HISTORY_DATABASE_URL", "")
    # Nome da tabela no banco SaaS (camelCase → usar aspas na query). Ex.: chatMessages
    SAAS_CHAT_MESSAGES_TABLE: str = os.getenv("SAAS_CHAT_MESSAGES_TABLE", "chatMessages")
    # Retries da reconciliação SaaS após consumir contexto (segundos após a resposta HTTP).
    # Lista separada por vírgula: ex. 30,60,120 = mais 3 passagens nesses intervalos (além da imediata).
    RECONCILE_SAAS_RETRY_DELAYS_SECONDS: str = os.getenv(
        "RECONCILE_SAAS_RETRY_DELAYS_SECONDS",
        "30,60,120",
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "10080")
    )  # 7 dias

    # CORS (origens exatas e opcional regex para ex.: *.easypanel.host)
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000"
    )
    # Regex para aceitar origens. Vazio = usa default abaixo (qualquer subdomínio Easypanel).
    CORS_ORIGIN_REGEX: str = os.getenv("CORS_ORIGIN_REGEX", "")

    # Evolution API (base - instâncias por tenant no DB)
    EVOLUTION_API_URL: str = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
    EVOLUTION_API_KEY: str = os.getenv("EVOLUTION_API_KEY", "")

    # Redis (filas / cache)
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # POST outbound para webhooks externos (n8n): false se HTTPS interno com certificado autoassinado
    WEBHOOK_VERIFY_SSL: bool = True

    # Segredo para POST /api/reception-context (n8n grava contexto após gerar msg_recepcao). Vazio = rota desativada (503).
    RECEPTION_CONTEXT_SECRET: str = os.getenv("RECEPTION_CONTEXT_SECRET", "")
    # Segredo para /api/qualification (n8n/agente grava respostas da qualificação). Vazio = rotas secretas desativadas.
    QUALIFICATION_SECRET: str = os.getenv("QUALIFICATION_SECRET", "")
    # Webhook padrão para respostas por palavras-chave (n8n).
    DEFAULT_CAMPAIGN_WEBHOOK_URL: str = os.getenv(
        "DEFAULT_CAMPAIGN_WEBHOOK_URL",
        "https://fabricaia-n8n.90qhxz.easypanel.host/webhook/controle-disparo",
    )

    # Onde a Evolution (na internet) deve chamar o MassFlow. É só o domínio do SEU backend, sem path.
    # Ex.: https://massflow-backend.seudominio.com ou https://api.seudominio.com
    # NÃO é URL da Evolution, nÃO é n8n. No Easypanel: copie a URL pública do serviço da API (mesma que responde /health).
    PUBLIC_BASE_URL: str = ""

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

    @property
    def cors_origin_regex(self) -> str:
        """Regex para CORS; se vazio, default permite qualquer subdomínio .easypanel.host."""
        s = (self.CORS_ORIGIN_REGEX or "").strip()
        if s:
            return s
        # Qualquer subdomínio: https://a.b.easypanel.host (um ou mais segmentos antes de .easypanel.host)
        return r"https://([a-z0-9-]+\.)+easypanel\.host"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
