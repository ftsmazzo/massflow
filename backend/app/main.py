"""
MassFlow API - Sistema de disparos em massa (Evolution API)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db

# Routers serão incluídos conforme as fases
# from app.routers import auth, tenants, leads, instances, campaigns


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


# init_db() é chamado pelo entrypoint.sh antes de subir o uvicorn (deploy Easypanel).
# Assim tabelas/migrações ocorrem na implantação, sem shell manual.


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


# Incluir routers (descomentar nas fases)
# app.include_router(auth.router, prefix="/api", tags=["Auth"])
# app.include_router(tenants.router, prefix="/api", tags=["Tenants"])
# app.include_router(leads.router, prefix="/api", tags=["Leads"])
# app.include_router(instances.router, prefix="/api", tags=["Instances"])
# app.include_router(campaigns.router, prefix="/api", tags=["Campaigns"])
