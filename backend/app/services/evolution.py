"""
Integração com Evolution API (versão mínima: 2.3.7).

Documentação oficial: https://doc.evolution-api.com/
- Send Media: https://doc.evolution-api.com/v2/api-reference/message-controller/send-media
- Índice v2: https://doc.evolution-api.com/llms.txt

Endpoints usados:
- POST /instance/create, GET /instance/connect/{instance}, GET /instance/connectionState/{instance}
- DELETE /instance/logout/{instance}
- POST /message/sendText/{instance}
- POST /message/sendMedia/{instance} — body: number, mediatype, mimetype, caption, media (URL ou base64), fileName
"""
import httpx
from typing import Any


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
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{base}/message/sendMedia/{instance_name}",
            json=body,
            headers=_headers(api_key),
        )
        r.raise_for_status()
        return r.json() if r.content else {}
