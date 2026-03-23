"""
Parse de webhooks da Evolution API (v2) para mensagens recebidas (inbound).

Mensagens com `key.fromMe == true` são ignoradas (eco do que a instância enviou).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_phone_digits(value: str | None) -> str:
    return "".join(c for c in str(value or "") if c.isdigit())


def _text_from_inner_message(msg_obj: dict[str, Any]) -> str:
    if not isinstance(msg_obj, dict):
        return ""
    if isinstance(msg_obj.get("conversation"), str):
        return msg_obj["conversation"]
    etm = msg_obj.get("extendedTextMessage")
    if isinstance(etm, dict) and isinstance(etm.get("text"), str):
        return etm["text"]
    for key in ("imageMessage", "videoMessage", "documentMessage", "audioMessage"):
        sub = msg_obj.get(key)
        if isinstance(sub, dict):
            cap = sub.get("caption")
            if isinstance(cap, str) and cap.strip():
                return cap
    return ""


def _phone_from_key(key: dict[str, Any]) -> str:
    remote_jid = key.get("remoteJid") or key.get("remote_jid")
    if isinstance(remote_jid, str) and "@" in remote_jid:
        return normalize_phone_digits(remote_jid.split("@", 1)[0])
    if isinstance(remote_jid, str):
        return normalize_phone_digits(remote_jid)
    return ""


def _iter_message_blocks(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        inner = data.get("messages")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
        return [data]
    if payload.get("key") or payload.get("message"):
        return [payload]
    return []


def extract_inbound_text_and_phone(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Extrai (texto, telefone) da primeira mensagem recebida (não fromMe)."""
    if isinstance(payload.get("text"), str) and payload["text"].strip():
        phone = normalize_phone_digits(payload.get("phone") or payload.get("number") or payload.get("from"))
        if phone:
            return (payload["text"].strip(), phone)
    if isinstance(payload.get("message"), str) and payload["message"].strip():
        phone = normalize_phone_digits(payload.get("phone") or payload.get("number") or payload.get("from"))
        if phone:
            return (payload["message"].strip(), phone)

    blocks = _iter_message_blocks(payload)
    event = payload.get("event")
    if not blocks:
        logger.debug("inbound_evolution: nenhum bloco (event=%s)", event)
        return None

    for block in blocks:
        key = block.get("key") if isinstance(block.get("key"), dict) else {}
        from_me = bool(key.get("fromMe") or key.get("from_me"))
        if from_me:
            continue

        phone = _phone_from_key(key)
        if not phone and isinstance(block.get("remoteJid"), str):
            rj = block["remoteJid"]
            phone = normalize_phone_digits(rj.split("@", 1)[0]) if "@" in rj else normalize_phone_digits(rj)

        inner = block.get("message")
        text = ""
        if isinstance(inner, dict):
            text = _text_from_inner_message(inner)
        if not text:
            if isinstance(block.get("body"), str):
                text = block["body"]
            elif isinstance(block.get("text"), str):
                text = block["text"]

        if text and text.strip() and phone:
            return (text.strip(), phone)

    return None


def phones_match_for_lead(inbound_digits: str, stored_phone: str) -> bool:
    a = inbound_digits
    b = normalize_phone_digits(stored_phone)
    if not a or not b:
        return False
    if a == b:
        return True

    def strip_br_country(x: str) -> str:
        if len(x) >= 12 and x.startswith("55"):
            return x[2:]
        return x

    a2, b2 = strip_br_country(a), strip_br_country(b)
    if a2 == b2:
        return True
    if len(a2) >= 11 and len(b2) >= 11 and a2[-11:] == b2[-11:]:
        return True
    if len(a2) >= 9 and len(b2) >= 9 and a2[-9:] == b2[-9:]:
        return True
    if a.endswith(b) or b.endswith(a):
        return True
    return False
