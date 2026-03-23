"""
Parse de webhooks da Evolution API (v2) para mensagens recebidas (inbound).

Mensagens com `key.fromMe == true` são ignoradas (eco do que a instância enviou).
Aceita também formato aninhado (lista, envelope HTTP em `body`, `data` como JSON string).
"""
from __future__ import annotations

import json
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


def normalize_inbound_payload(raw: Any) -> dict[str, Any] | None:
    """
    Evolution costuma enviar um objeto; alguns proxies ou testes enviam lista [ {...} ].
    `data` às vezes vem como string JSON.
    """
    p = raw
    if isinstance(p, list) and len(p) > 0:
        p = p[0]
    if not isinstance(p, dict):
        return None
    if isinstance(p.get("data"), str):
        try:
            inner = json.loads(p["data"])
            if isinstance(inner, dict):
                p = {**p, "data": inner}
        except (json.JSONDecodeError, TypeError):
            pass

    # Envelope: payload Evolution aninhado em `body` (não confundir com body { sender, content })
    b = p.get("body")
    if isinstance(b, dict):
        is_sender_content_shape = isinstance(b.get("sender"), dict) and b.get("content") is not None
        looks_evolution = bool(
            b.get("event") or b.get("data") or b.get("key") or b.get("message")
        )
        if not is_sender_content_shape and looks_evolution:
            p = b
    elif isinstance(b, str):
        try:
            inner_b = json.loads(b)
            if isinstance(inner_b, dict):
                is_sender_content_shape = isinstance(inner_b.get("sender"), dict) and inner_b.get("content") is not None
                looks_evolution = bool(
                    inner_b.get("event") or inner_b.get("data") or inner_b.get("key")
                )
                if not is_sender_content_shape and looks_evolution:
                    p = inner_b
        except (json.JSONDecodeError, TypeError):
            pass

    return p


def _extract_from_sender_content_body(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Formato alternativo: body.content (texto) + body.sender (telefone/identifier)."""
    b = payload.get("body")
    if not isinstance(b, dict):
        return None
    msg = b.get("content")
    if not isinstance(msg, str) or not msg.strip():
        return None
    sender = b.get("sender") if isinstance(b.get("sender"), dict) else {}
    phone = ""
    if isinstance(sender.get("phone_number"), str):
        phone = normalize_phone_digits(sender["phone_number"])
    if not phone and isinstance(sender.get("identifier"), str):
        ident = sender["identifier"]
        if "@" in ident:
            phone = normalize_phone_digits(ident.split("@", 1)[0])
        else:
            phone = normalize_phone_digits(ident)
    if msg.strip() and phone:
        return (msg.strip(), phone)
    return None


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


def extract_inbound_text_and_phone(raw: Any) -> tuple[str, str] | None:
    """Extrai (texto, telefone) da primeira mensagem recebida (não fromMe)."""
    payload = normalize_inbound_payload(raw)
    if not payload:
        return None

    cw = _extract_from_sender_content_body(payload)
    if cw:
        return cw

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
        logger.debug("inbound_evolution: nenhum bloco (event=%s keys=%s)", event, list(payload.keys())[:15])
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
