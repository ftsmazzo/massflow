"""
Integração com Evolution API: criar instância, conectar (QR), status.
"""
import httpx
from typing import Any

# Evolution API v2
# POST /instance/create - body: instanceName, integration (WHATSAPP-BAILEYS | WHATSAPP-BUSINESS), token?
# GET /instance/connect/{instance} - retorna pairingCode, code (QR), count
# GET /instance/connectionState/{instance} - status da conexão (opcional)


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
