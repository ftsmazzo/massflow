# MassFlow Backend - FastAPI
FROM python:3.11-slim

WORKDIR /app

# Dependências do sistema (psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Entrypoint: aplica banco (init_db / depois alembic upgrade) e sobe a API na implantação
RUN chmod +x entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
