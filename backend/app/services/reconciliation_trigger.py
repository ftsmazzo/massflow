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


def attach_reconcile_jobs_after_context_consumed(
    background_tasks: BackgroundTasks,
    tenant_id: int,
    campaign_id: int,
    lead_phone: str,
    lead_id: int | None,
    lead_name: str | None,
) -> dict[str, Any]:
    """
    1) Após responder o GET, roda reconciliação em background (não bloqueia o agente).
    2) Repete após RECONCILE_SAAS_DELAY_SECONDS para capturar mensagens que ainda não estavam no SaaS.
    """
    out: dict[str, Any] = {
        "reconcile_saas_scheduled": False,
        "reconcile_saas_delayed_seconds": None,
    }
    if not (settings.SAAS_CHAT_HISTORY_DATABASE_URL or "").strip():
        return out

    delay = max(0, int(settings.RECONCILE_SAAS_DELAY_SECONDS or 0))

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

    if delay > 0:
        out["reconcile_saas_delayed_seconds"] = delay

        def _delayed() -> None:
            time.sleep(delay)
            run_reconcile_safe(
                tenant_id,
                campaign_id,
                lead_phone,
                lead_id,
                lead_name,
                "delayed",
            )

        t = threading.Thread(target=_delayed, name="reconcile-saas-delayed", daemon=True)
        t.start()

    return out
