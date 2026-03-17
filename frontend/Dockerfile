# MassFlow Frontend - React/Vite
# Build context: RAIZ do repositório (Easypanel e docker-compose).
# No Easypanel: defina Build Arg VITE_API_URL com a URL do backend (ex: https://...-backend....easypanel.host)
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
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
