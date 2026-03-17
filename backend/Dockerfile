# MassFlow Backend - FastAPI
# Build context: RAIZ do repositório (obrigatório).
# Easypanel: context = repo, Dockerfile = backend/Dockerfile
# Local: docker compose com context: . e dockerfile: backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

RUN chmod +x entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
