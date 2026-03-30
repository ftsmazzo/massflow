"""
Dispara reconciliação SaaS (chatMessages → qualificação) em background.
Chamado ao consumir contexto de recepção (agente iniciou atendimento) e em retry tardio.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from fastapi import BackgroundTasks

from app.config import settings
from app.database import SessionLocal
from app.services.saas_reconciliation import reconcile_lead_from_saas_chat
from app.services.saas_chat_messages import saas_database_configured

logger = logging.getLogger("massflow.reconcile")


def run_reconcile_safe(
    tenant_id: int,
    campaign_id: int,
    lead_phone: str,
    lead_id: int | None,
    lead_name: str | None,
    attempt: str = "immediate",
) -> None:
    """Executa reconciliação em sessão DB própria; nunca propaga exceção."""
    db = SessionLocal()
    try:
        out = reconcile_lead_from_saas_chat(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            lead_phone=lead_phone,
            lead_id=lead_id,
            lead_name=lead_name,
        )
        logger.info(
            "reconcile_saas %s tenant=%s campaign=%s phone=%s steps=%s classification=%s",
            attempt,
            tenant_id,
            campaign_id,
            lead_phone,
            out.get("steps_applied"),
            out.get("classification"),
        )
    except ValueError as e:
        logger.warning("reconcile_saas %s tenant=%s campaign=%s: %s", attempt, tenant_id, campaign_id, e)
    except Exception:
        logger.exception(
            "reconcile_saas %s tenant=%s campaign=%s phone=%s",
            attempt,
            tenant_id,
            campaign_id,
            lead_phone,
        )
    finally:
        db.close()


def _parse_retry_delays() -> list[int]:
    raw = (getattr(settings, "RECONCILE_SAAS_RETRY_DELAYS_SECONDS", None) or "30,60,120") or ""
    out: list[int] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
            if n > 0:
                out.append(n)
        except ValueError:
            continue
    return out


def attach_reconcile_jobs_after_context_consumed(
    background_tasks: BackgroundTasks,
    tenant_id: int,
    campaign_id: int,
    lead_phone: str,
    lead_id: int | None,
    lead_name: str | None,
) -> dict[str, Any]:
    """
    1) Após responder o GET, reconciliação imediata em background.
    2) Retries em janelas curtas (RECONCILE_SAAS_RETRY_DELAYS_SECONDS) até o SaaS refletir todas as mensagens.
    """
    out: dict[str, Any] = {
        "reconcile_saas_scheduled": False,
        "reconcile_saas_retry_delays_seconds": [],
    }
    if not saas_database_configured():
        return out

    delays = _parse_retry_delays()

    background_tasks.add_task(
        run_reconcile_safe,
        tenant_id,
        campaign_id,
        lead_phone,
        lead_id,
        lead_name,
        "immediate",
    )
    out["reconcile_saas_scheduled"] = True
    out["reconcile_saas_retry_delays_seconds"] = delays

    for i, delay in enumerate(delays):

        def _make_delayed(sec: int, idx: int) -> None:
            def _run() -> None:
                time.sleep(sec)
                run_reconcile_safe(
                    tenant_id,
                    campaign_id,
                    lead_phone,
                    lead_id,
                    lead_name,
                    f"retry_{idx}_{sec}s",
                )

            return _run

        t = threading.Thread(
            target=_make_delayed(delay, i),
            name=f"reconcile-saas-{delay}s",
            daemon=True,
        )
        t.start()

    return out
