"""
MassFlow API - Sistema de disparos em massa (Evolution API)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, tenants


app = FastAPI(
    title="MassFlow API",
    description="Sistema de disparos em massa via Evolution API - Captação de leads e campanhas",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
