"""
MassFlow API - Sistema de disparos em massa (Evolution API)
"""
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tenants, instances


def _origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    if origin in settings.cors_origins_list:
        return True
    try:
        return bool(re.fullmatch(settings.cors_origin_regex, origin))
    except re.error:
        return False


class InjectCorsHeadersMiddleware(BaseHTTPMiddleware):
    """Garante Access-Control-Allow-Origin em todas as respostas quando Origin é permitido."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin", "").strip()
        if not _origin_allowed(origin):
            return response
        if hasattr(response, "body") and response.body is not None:
            headers = dict(response.headers)
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            return Response(content=response.body, status_code=response.status_code, headers=headers)
        return response


class OptionsCORSMiddleware(BaseHTTPMiddleware):
    """Responde 200 a OPTIONS (preflight) com headers CORS, para evitar 405 em proxies."""

    async def dispatch(self, request: Request, call_next):
        if request.method != "OPTIONS":
            return await call_next(request)
        origin = request.headers.get("origin", "").strip()
        if not origin and settings.cors_origins_list:
            origin = settings.cors_origins_list[0]
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

# Ordem: o primeiro add_middleware é o último a processar a request (primeiro a ver a response).
# InjectCorsHeaders: injeta CORS em toda resposta quando Origin é permitido.
app.add_middleware(InjectCorsHeadersMiddleware)
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
