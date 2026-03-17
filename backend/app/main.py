"""
MassFlow API - Sistema de disparos em massa (Evolution API)
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tenants, instances


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

# OPTIONS primeiro (preflight sempre 200); depois CORS nas demais respostas
app.add_middleware(OptionsCORSMiddleware)

# CORS: lista exata + opcional regex (ex.: CORS_ORIGIN_REGEX=https://.*\.easypanel\.host)
cors_kw: dict = {
    "allow_origins": settings.cors_origins_list,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["*"],
}
if getattr(settings, "CORS_ORIGIN_REGEX", None) and settings.CORS_ORIGIN_REGEX.strip():
    cors_kw["allow_origin_regex"] = settings.CORS_ORIGIN_REGEX.strip()
app.add_middleware(CORSMiddleware, **cors_kw)


# Migrações: entrypoint.sh roda `alembic upgrade head` antes do uvicorn (deploy Easypanel).


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
