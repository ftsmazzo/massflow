# MassFlow Frontend - React/Vite
# Build context: RAIZ do repositório (Easypanel e docker-compose).
# Produção: NÃO defina VITE_API_URL no build; no container defina BACKEND_URL (ex: http://massflow-backend:8000).
# O nginx faz proxy de /api para o backend = mesma origem = sem CORS.
FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY frontend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
