"""
Leitura da tabela de histórico de chat no Postgres SaaS (ex.: chatMessages).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from urllib.parse import quote_plus

from app.config import settings

logger = logging.getLogger("massflow.saas_chat")


def normalize_saas_database_url(url: str) -> str:
    """
    Corrige erro comum: porta antes do host (psycopg2 interpreta o host como '1524@dominio').

    Errado:  postgresql://u:p@1524@easypanel.exemplo.com/db
    Certo:    postgresql://u:p@easypanel.exemplo.com:1524/db

    Senhas com '@' devem ser URL-encoded (%40); esta rotina não altera isso.
    """
    s = (url or "").strip()
    if not s:
        return s
    # Padrão: @<porta numérica>@<hostname> → @<hostname>:<porta>
    fixed = re.sub(
        r"@(\d{2,5})@([a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?)",
        r"@\2:\1",
        s,
        count=1,
    )
    if fixed != s:
        logger.warning(
            "SAAS_CHAT_HISTORY_DATABASE_URL foi normalizada (porta estava antes do host). "
            "Prefira já usar o formato postgresql://user:pass@HOST:PORT/db"
        )
    return fixed


def get_effective_saas_database_url() -> str:
    """
    Se SAAS_PG_HOST + SAAS_PG_USER + SAAS_PG_DATABASE estiverem definidos, monta a URL com
    quote_plus na senha (aceita @, :, etc. sem editar a string na mão).
    Caso contrário usa SAAS_CHAT_HISTORY_DATABASE_URL (com normalização @porta@host).
    """
    h = (getattr(settings, "SAAS_PG_HOST", "") or "").strip()
    user = (getattr(settings, "SAAS_PG_USER", "") or "").strip()
    dbn = (getattr(settings, "SAAS_PG_DATABASE", "") or "").strip()
    if h and user and dbn:
        pw = getattr(settings, "SAAS_PG_PASSWORD", "") or ""
        port = int(getattr(settings, "SAAS_PG_PORT", 5432) or 5432)
        ssl = (getattr(settings, "SAAS_PG_SSLMODE", "require") or "require").strip()
        pu, pp = quote_plus(user), quote_plus(pw)
        return f"postgresql://{pu}:{pp}@{h}:{port}/{dbn}?sslmode={ssl}"
    raw = (settings.SAAS_CHAT_HISTORY_DATABASE_URL or "").strip()
    return normalize_saas_database_url(raw)


def saas_database_configured() -> bool:
    return bool(get_effective_saas_database_url().strip())


def _validate_saas_url(url: str) -> None:
    """Garante que a URL do Postgres SaaS seja parseável e o host não contenha '@'."""
    try:
        u = make_url(url)
    except Exception as e:
        raise ValueError(
            "URL do Postgres SaaS inválida. Use SAAS_PG_* (host, user, password, database) "
            "ou SAAS_CHAT_HISTORY_DATABASE_URL no formato postgresql://user:pass@HOST:PORT/db"
        ) from e
    host = (u.host or "").strip()
    if "@" in host:
        raise ValueError(
            "URL do SaaS malformada: a porta deve ficar depois do host "
            "(postgresql://user:pass@easypanel.exemplo.com:1524/db), "
            "não como @1524@easypanel.exemplo.com."
        )


@dataclass
class SaaSChatRow:
    id: int
    tenant_id: int | None
    user_message: str | None
    bot_content: str | None
    created_at: datetime | None
    phone_raw: str | None


def _engine() -> Engine:
    url = get_effective_saas_database_url()
    if not url:
        raise RuntimeError(
            "Postgres SaaS não configurado: defina SAAS_PG_HOST/USER/DATABASE "
            "ou SAAS_CHAT_HISTORY_DATABASE_URL."
        )
    _validate_saas_url(url)
    return create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=2)


def fetch_chat_messages_for_phone(
    phone_digits: str,
    saas_tenant_id: int | None = None,
    limit: int = 500,
) -> list[SaaSChatRow]:
    """
    Busca linhas da tabela configurada em SAAS_CHAT_MESSAGES_TABLE (default chatMessages),
    filtrando pelo telefone (substring nos dígitos).
    """
    digits = "".join(c for c in str(phone_digits or "") if c.isdigit())
    if len(digits) < 10:
        raise ValueError("Telefone inválido para busca SaaS.")

    table = (settings.SAAS_CHAT_MESSAGES_TABLE or "chatMessages").strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table):
        raise ValueError("Nome de tabela SaaS inválido (use apenas letras, números e _).")
    table_sql = f'"{table}"'

    eng = _engine()
    like = f"%{digits}%"

    tenant_filter = ""
    params: dict[str, Any] = {"like": like, "lim": limit}
    if saas_tenant_id is not None:
        tenant_filter = ' AND "tenantId" = :tid'
        params["tid"] = int(saas_tenant_id)

    sql = text(
        f"""
        SELECT id, "tenantId", "userMessage", content, "createdAt", phone
        FROM {table_sql}
        WHERE (phone LIKE :like OR phone LIKE :like2)
        {tenant_filter}
        ORDER BY "createdAt" ASC NULLS LAST, id ASC
        LIMIT :lim
        """
    )
    params["like2"] = f"%{digits}@%"

    out: list[SaaSChatRow] = []
    with eng.connect() as conn:
        result = conn.execute(sql, params)
        for row in result.mappings():
            out.append(
                SaaSChatRow(
                    id=int(row["id"]),
                    tenant_id=int(row["tenantId"]) if row.get("tenantId") is not None else None,
                    user_message=row.get("userMessage"),
                    bot_content=row.get("content"),
                    created_at=row.get("createdAt"),
                    phone_raw=row.get("phone"),
                )
            )
    return out
