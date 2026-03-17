#!/bin/sh
# Executado na implantação (Easypanel): aplica banco e sobe a API.
# Nada de steps manuais em shell para o banco.

set -e
echo "MassFlow Backend: aplicando migrações..."
alembic upgrade head
echo "Banco pronto."
echo "Iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
