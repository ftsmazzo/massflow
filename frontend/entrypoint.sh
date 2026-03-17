#!/bin/sh
# Gera nginx.conf a partir do template com BACKEND_URL (env do container).
set -e
export BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
envsubst '${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g "daemon off;"
