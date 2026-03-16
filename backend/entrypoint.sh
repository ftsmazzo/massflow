#!/bin/sh
# Executado na implantação (Easypanel): aplica banco e sobe a API.
# Nada de steps manuais em shell para o banco.

set -e
echo "MassFlow Backend: aplicando banco..."
python -c "
from app.database import init_db
init_db()
print('Banco pronto.')
"
echo "Iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
