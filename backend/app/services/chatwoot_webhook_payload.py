"""
Monta o corpo JSON no formato do webhook Chatwoot (evento message_created / incoming).

O n8n costuma receber o mesmo formato que o Chatwoot envia ao disparar automações;
o MassFlow pode replicar essa forma para o agente de IA processar como se fosse mensagem real.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from app.services.inbound_evolution import normalize_phone_digits


def _now_iso_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _e164_and_whatsapp_jid(phone_raw: str) -> tuple[str, str]:
    """Retorna (+5511..., 5511...@s.whatsapp.net) a partir do telefone salvo no lead."""
    d = normalize_phone_digits(phone_raw)
    if not d:
        return "+5500000000000", "5500000000000@s.whatsapp.net"
    if not d.startswith("55") and len(d) >= 10:
        d = "55" + d
    return f"+{d}", f"{d}@s.whatsapp.net"


def build_massflow_simple_payload(
    *,
    tenant_id: int,
    campaign_id: int,
    lead_id: int,
    lead_name: str,
    lead_phone: str,
    inbound_text: str,
    matched_keywords: list[str],
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "campaign_id": campaign_id,
        "lead_id": lead_id,
        "lead_name": lead_name,
        "lead_phone": lead_phone,
        "lead_message": inbound_text,
        "matched_keywords": matched_keywords,
        "source": "massflow_campaign_reply",
    }


def build_chatwoot_message_created_payload(
    *,
    tenant_id: int,
    campaign_id: int,
    lead_id: int,
    lead_name: str,
    lead_phone_raw: str,
    inbound_text: str,
    matched_keywords: list[str],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Estrutura alinhada ao webhook Chatwoot `message_created` (mensagem incoming).

    `overrides` pode vir de `campaign.content.response_webhook_chatwoot`, ex.:
    {"account": {"id": 1, "name": "Fabrica IA"}, "inbox": {"id": 119, "name": "Assistente LVA"}}
    """
    overrides = overrides or {}
    phone_e164, wa_jid = _e164_and_whatsapp_jid(lead_phone_raw)
    created_iso = _now_iso_z()
    ts = int(time.time())

    account = overrides.get("account") if isinstance(overrides.get("account"), dict) else None
    if not account:
        account = {"id": 1, "name": "MassFlow"}
    inbox = overrides.get("inbox") if isinstance(overrides.get("inbox"), dict) else None
    if not inbox:
        inbox = {"id": 0, "name": "MassFlow"}

    account_id = int(account.get("id", 1))
    inbox_id = int(inbox.get("id", 0))

    message_id = int(ts * 1000) % 2_147_483_647 or 1
    conversation_id = campaign_id * 1_000_000 + lead_id

    sender_core: dict[str, Any] = {
        "additional_attributes": {},
        "custom_attributes": {},
        "email": None,
        "id": lead_id,
        "identifier": wa_jid,
        "name": lead_name,
        "phone_number": phone_e164,
        "thumbnail": None,
        "blocked": False,
    }

    inner_message: dict[str, Any] = {
        "id": message_id,
        "content": inbound_text,
        "account_id": account_id,
        "inbox_id": inbox_id,
        "conversation_id": conversation_id,
        "message_type": 0,
        "created_at": ts,
        "updated_at": created_iso,
        "private": False,
        "status": "sent",
        "source_id": f"WAID:MF-{campaign_id}-{lead_id}-{message_id}",
        "content_type": "text",
        "content_attributes": {"in_reply_to": None},
        "sender_type": "Contact",
        "sender_id": lead_id,
        "external_source_ids": {},
        "additional_attributes": {},
        "processed_message_content": inbound_text,
        "sentiment": {},
        "conversation": {
            "assignee_id": None,
            "unread_count": 1,
            "last_activity_at": ts,
            "contact_inbox": {"source_id": f"massflow-{lead_id}"},
        },
        "sender": {
            **sender_core,
            "type": "contact",
        },
    }

    body: dict[str, Any] = {
        "account": account,
        "additional_attributes": {
            "massflow": {
                "tenant_id": tenant_id,
                "campaign_id": campaign_id,
                "lead_id": lead_id,
                "matched_keywords": matched_keywords,
                "source": "massflow_campaign_reply",
            }
        },
        "content_attributes": {"in_reply_to": None},
        "content_type": "text",
        "content": inbound_text,
        "conversation": {
            "additional_attributes": {},
            "can_reply": True,
            "channel": "Channel::Api",
            "contact_inbox": {
                "id": lead_id,
                "contact_id": lead_id,
                "inbox_id": inbox_id,
                "source_id": f"massflow-{lead_id}",
                "created_at": created_iso,
                "updated_at": created_iso,
                "hmac_verified": False,
                "pubsub_token": "",
            },
            "id": conversation_id,
            "inbox_id": inbox_id,
            "messages": [inner_message],
            "labels": [],
            "meta": {
                "sender": {**sender_core, "type": "contact"},
                "assignee": None,
                "assignee_type": None,
                "team": None,
                "hmac_verified": False,
            },
            "status": "open",
            "custom_attributes": {},
            "snoozed_until": None,
            "unread_count": 1,
            "last_activity_at": ts,
            "timestamp": ts,
            "created_at": ts,
            "updated_at": float(ts),
        },
        "created_at": created_iso,
        "id": message_id,
        "inbox": inbox,
        "message_type": "incoming",
        "private": False,
        "sender": {
            "account": account,
            **sender_core,
            "avatar": None,
        },
        "source_id": inner_message["source_id"],
        "event": "message_created",
    }

    # Mescla campos extras do Chatwoot (deep merge superficial em account/inbox já feito)
    extra = overrides.get("extra_root_fields")
    if isinstance(extra, dict):
        for k, v in extra.items():
            if k not in body:
                body[k] = v

    return body


def resolve_outbound_payload(
    content: dict[str, Any],
    *,
    tenant_id: int,
    campaign_id: int,
    lead_id: int,
    lead_name: str,
    lead_phone: str,
    inbound_text: str,
    matched_keywords: list[str],
) -> dict[str, Any]:
    """Escolhe formato do POST para o webhook do n8n conforme `response_webhook_format`."""
    # Padrão chatwoot: compatível com workflows n8n que esperam o webhook do Chatwoot.
    fmt = str(content.get("response_webhook_format") or "chatwoot").strip().lower()
    if fmt in ("massflow", "simple", "legacy"):
        return build_massflow_simple_payload(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            lead_name=lead_name,
            lead_phone=lead_phone,
            inbound_text=inbound_text,
            matched_keywords=matched_keywords,
        )
    overrides = content.get("response_webhook_chatwoot")
    if not isinstance(overrides, dict):
        overrides = {}
    return build_chatwoot_message_created_payload(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        lead_name=lead_name,
        lead_phone_raw=lead_phone,
        inbound_text=inbound_text,
        matched_keywords=matched_keywords,
        overrides=overrides,
    )
