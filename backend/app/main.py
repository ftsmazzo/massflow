"""
MassFlow API - Sistema de disparos em massa (Evolution API)
"""
import re
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tenants, instances, shielding, contacts, lists, tags


def _origin_allowed(origin: str) -> bool:
    if not origin or not origin.startswith("https://"):
        return False
    if origin in settings.cors_origins_list:
        return True
    try:
        if re.fullmatch(settings.cors_origin_regex, origin):
            return True
    except re.error:
        pass
    # Fallback: qualquer origem .easypanel.host (evita bloqueio em produção)
    if ".easypanel.host" in origin:
        return True
    return False


def _get_origin_from_scope(scope: Scope) -> str:
    for key, value in scope.get("headers", []):
        if key == b"origin":
            return value.decode("latin-1").strip()
    return ""


class CorsInjectASGIMiddleware:
    """ASGI puro: injeta CORS em TODAS as respostas (incl. erros) quando Origin é permitido."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        origin = _get_origin_from_scope(scope)
        allowed = _origin_allowed(origin)

        async def send_with_cors(message: Message) -> None:
            if message["type"] == "http.response.start" and allowed and origin:
                headers = MutableHeaders(raw=message["headers"])
                headers["Access-Control-Allow-Origin"] = origin
                headers["Access-Control-Allow-Credentials"] = "true"
            await send(message)

        await self.app(scope, receive, send_with_cors)


class OptionsCORSMiddleware(BaseHTTPMiddleware):
    """Responde 200 a OPTIONS (preflight) com headers CORS."""

    async def dispatch(self, request: Request, call_next):
        if request.method != "OPTIONS":
            return await call_next(request)
        origin = request.headers.get("origin", "").strip()
        if not origin and settings.cors_origins_list:
            origin = settings.cors_origins_list[0]
        if not origin:
            origin = _get_origin_from_scope(request.scope)
        headers = {
            "Allow": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Max-Age": "86400",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        }
        if origin:
            headers["Access-Control-Allow-Origin"] = origin
        return Response(status_code=200, headers=headers)


app = FastAPI(
    title="MassFlow API",
    description="Sistema de disparos em massa via Evolution API - Captação de leads e campanhas",
    version="0.1.0",
)

# CORS: middleware ASGI injeta headers em TODAS as respostas (incl. 500/422).
app.add_middleware(CorsInjectASGIMiddleware)
# OPTIONS (preflight) sempre 200.
app.add_middleware(OptionsCORSMiddleware)

# CORS: lista exata + opcional regex (ex.: CORS_ORIGIN_REGEX=https://.*\.easypanel\.host)
cors_kw: dict = {
    "allow_origins": settings.cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
}
cors_kw["allow_origin_regex"] = settings.cors_origin_regex
app.add_middleware(CORSMiddleware, **cors_kw)


# Migrações: entrypoint.sh roda `alembic upgrade head` antes do uvicorn (deploy Easypanel).


@app.get("/")
async def root():
    """Resposta na raiz para health check de proxies (GET /)."""
    return {"status": "ok", "service": "massflow-api"}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "massflow-api"}


@app.get("/api/status")
async def api_status():
    return {
        "message": "MassFlow API",
        "status": "online",
        "version": "0.1.0",
    }


app.include_router(auth.router, prefix="/api")
app.include_router(tenants.router, prefix="/api")
app.include_router(instances.router, prefix="/api")
app.include_router(shielding.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(lists.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
