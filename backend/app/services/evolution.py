"""
Integração com Evolution API (versão alvo / mínima: 2.3.7).

Referência de release que você usa no servidor; paths em doc.evolution-api.com usam /v2/ na URL,
mas o contrato validado para este projeto é o da Evolution 2.3.7 (ex.: coleção Postman 2.3.7).

Documentação oficial: https://doc.evolution-api.com/
- Set Webhook: https://doc.evolution-api.com/v2/api-reference/webhook/set
- Send Media: https://doc.evolution-api.com/v2/api-reference/message-controller/send-media
- Índice: https://doc.evolution-api.com/llms.txt

Endpoints usados:
- POST /instance/create, GET /instance/connect/{instance}, GET /instance/connectionState/{instance}
- DELETE /instance/logout/{instance}
- POST /message/sendText/{instance}
- POST /message/sendMedia/{instance} — body: number, mediatype, mimetype, caption, media (URL ou base64), fileName
"""
import httpx
from typing import Any
from urllib.parse import quote


def _headers(api_key: str) -> dict:
    return {"apikey": api_key or "", "Content-Type": "application/json"}


def _base(url: str) -> str:
    return url.rstrip("/")


async def create_instance(api_url: str, api_key: str, instance_name: str) -> dict[str, Any]:
    """Cria uma instância na Evolution API (WHATSAPP-BAILEYS)."""
    base = _base(api_url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(
            f"{base}/instance/create",
            json={
                "instanceName": instance_name,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": False,
            },
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json()


async def connect_instance(api_url: str, api_key: str, instance_name: str) -> dict[str, Any]:
    """Gera QR code / pairing code para conectar a instância ao WhatsApp."""
    base = _base(api_url)
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(
            f"{base}/instance/connect/{instance_name}",
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json()


async def fetch_connection_state(api_url: str, api_key: str, instance_name: str) -> dict[str, Any] | None:
    """Consulta estado da conexão da instância (Evolution API)."""
    base = _base(api_url)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{base}/instance/connectionState/{instance_name}",
                headers=_headers(api_key),
            )
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
    except (httpx.HTTPError, Exception):
        return None


async def disconnect_instance(api_url: str, api_key: str, instance_name: str) -> dict[str, Any]:
    """Desconecta a instância do WhatsApp (Evolution API: DELETE /instance/logout)."""
    base = _base(api_url)
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.delete(
            f"{base}/instance/logout/{instance_name}",
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json() if r.content else {}


def send_text_sync(
    api_url: str,
    api_key: str,
    instance_name: str,
    number: str,
    text: str,
) -> dict[str, Any]:
    """Envia mensagem de texto via Evolution API (síncrono, para uso em thread)."""
    base = _base(api_url)
    number_clean = "".join(c for c in str(number) if c.isdigit())
    if not number_clean:
        raise ValueError("Número inválido")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{base}/message/sendText/{instance_name}",
            json={"number": number_clean, "text": text},
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json() if r.content else {}


def _normalize_media_base64(media_base64: str) -> str:
    """Retorna apenas o base64 puro; Evolution API pode rejeitar data:...;base64, com 400."""
    if not media_base64:
        return ""
    s = media_base64.strip()
    if s.startswith("data:") and ";base64," in s:
        return s.split(";base64,", 1)[1]
    return s


def send_media_sync(
    api_url: str,
    api_key: str,
    instance_name: str,
    number: str,
    mediatype: str,
    mimetype: str,
    caption: str,
    media_base64: str,
    file_name: str,
) -> dict[str, Any]:
    """Envia mídia (imagem, vídeo, documento, áudio) via Evolution API - arquivo em base64, não link."""
    base = _base(api_url)
    number_clean = "".join(c for c in str(number) if c.isdigit())
    if not number_clean:
        raise ValueError("Número inválido")
    if not media_base64:
        raise ValueError("Mídia em base64 é obrigatória")
    media_value = _normalize_media_base64(media_base64)
    if not media_value:
        raise ValueError("Mídia em base64 inválida")
    body = {
        "number": number_clean,
        "mediatype": mediatype,
        "mimetype": mimetype,
        "caption": caption or "",
        "media": media_value,
        "fileName": file_name or "file",
    }
    with httpx.Client(timeout=90.0) as client:
        r = client.post(
            f"{base}/message/sendMedia/{instance_name}",
            json=body,
            headers=_headers(api_key),
        )
        if not r.is_success:
            err_detail = r.text[:500] if r.text else r.reason_phrase
            raise ValueError(f"Evolution API {r.status_code}: {err_detail}")
        return r.json() if r.content else {}


def check_whatsapp_numbers_sync(
    api_url: str,
    api_key: str,
    instance_name: str,
    numbers: list[str],
) -> dict[str, bool]:
    """
    POST /chat/whatsappNumbers/{instance} (Evolution 2.3.7).
    Retorna mapa numero->exists para os números informados.
    """
    base = _base(api_url)
    safe = quote(instance_name, safe="")
    digits = ["".join(c for c in str(n or "") if c.isdigit()) for n in numbers]
    payload_numbers = [n for n in digits if n]
    if not payload_numbers:
        return {}
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            f"{base}/chat/whatsappNumbers/{safe}",
            json={"numbers": payload_numbers},
            headers=_headers(api_key),
        )
        r.raise_for_status()
        data = r.json() if r.content else []
    out: dict[str, bool] = {}
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            num = "".join(c for c in str(item.get("number") or "") if c.isdigit())
            if not num:
                continue
            out[num] = bool(item.get("exists"))
    return out


def find_webhook_sync(api_url: str, api_key: str, instance_name: str) -> dict[str, Any]:
    """
    GET /webhook/find/{instance} (Evolution API 2.3.7) — URL e eventos configurados na instância.
    """
    base = _base(api_url)
    safe = quote(instance_name, safe="")
    with httpx.Client(timeout=20.0) as client:
        r = client.get(
            f"{base}/webhook/find/{safe}",
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json() if r.content else {}


def set_webhook_sync(
    api_url: str,
    api_key: str,
    instance_name: str,
    webhook_url: str,
) -> dict[str, Any]:
    """
    POST /webhook/set/{instance} (Evolution API 2.3.7 — mesmo contrato da doc / Postman).
    Uma URL para todas as linhas: webhookByEvents=false; o payload de saída inclui `instance`.
    """
    base = _base(api_url)
    safe = quote(instance_name, safe="")
    payload = {
        "enabled": True,
        "url": webhook_url,
        "webhookByEvents": False,
        "webhookBase64": False,
        "events": ["MESSAGES_UPSERT"],
    }
    with httpx.Client(timeout=45.0) as client:
        r = client.post(
            f"{base}/webhook/set/{safe}",
            json=payload,
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json() if r.content else {}
