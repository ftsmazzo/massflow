# MassFlow — Documento de Implantação

Ordem lógica dos passos para implantar o MassFlow em **Projetos-FabriaIA** (pasta `MassFlow/`). Requisitos completos em **MassFlow_ESPECIFICACAO_FINAL.md** (tags/funis, IA integrada, contatos manual/CSV/API, modelo SaaS 3 níveis + créditos, integração Agentes SaaS). Repositório, tecnologias, estrutura (um serviço por pasta com Dockerfile), Easypanel + GitHub.

---

## 1. Visão da arquitetura de serviços

### 1.1 Regra: uma pasta com Dockerfile = um serviço no Easypanel

- Cada **pasta na raiz do repositório** que contém um **Dockerfile** corresponde a **um serviço** no Easypanel.
- O Easypanel conecta ao repositório GitHub e usa o Dockerfile da pasta escolhida para build e deploy.
- Exemplo: `backend/` com Dockerfile → serviço "MassFlow Backend"; `frontend/` com Dockerfile → serviço "MassFlow Frontend".

### 1.2 Serviços recomendados

| Serviço        | Pasta      | Responsabilidade |
|----------------|------------|------------------|
| **Backend (API)** | `backend/` | API REST (FastAPI), autenticação, tenants, campanhas, leads, instâncias, webhook Evolution, fila de jobs (ou chamadas internas), integrações. |
| **Frontend (SPA)** | `frontend/` | Interface do usuário (React/Vite). Build estático; em produção pode ser servido por nginx (próprio container) ou pelo backend (opcional). |
| **PostgreSQL** | —          | Banco de dados. Pode ser serviço do Easypanel ou externo (ex.: Supabase, Neon). |
| **Redis** (opcional Fase 1) | — | Filas (disparo de campanhas, processamento de webhook). Incluir quando houver workers assíncronos. |

**Resposta direta:** Sim, faz sentido ter **backend** e **frontend** como no Devocional — dois serviços (duas pastas com Dockerfile). Assim cada um escala e atualiza independente. Se quiser simplificar no início, o backend pode servir o build do frontend (um único serviço); o documento considera **dois serviços** como padrão.

Serviços adicionais (definidos depois por pasta + Dockerfile):
- **Worker** (opcional): `worker/` — consome fila Redis, processa disparo de campanhas e webhooks pesados. Pode ser incorporado ao backend no início (cron/thread) e separado depois.

---

## 2. Tecnologias recomendadas

| Camada | Tecnologia | Motivo |
|--------|------------|--------|
| **Backend** | **FastAPI (Python 3.11+)** | Alinhado ao Devocional e à visão; async; documentação automática; tipo de dados com Pydantic. |
| **Frontend** | **React 18 + TypeScript + Vite** | SPA moderna, rápida, tipada; fácil deploy estático. |
| **Banco de dados** | **PostgreSQL 15+** | Multi-tenant, JSON para campos custom, full-text; já usado no contexto. |
| **Filas / cache** | **Redis 7** | Filas para campanhas (Celery, RQ ou Bull) e cache; opcional na Fase 1. |
| **API WhatsApp** | **Evolution API** | Já adotada; não oficial; instâncias por tenant. |
| **Auth** | **JWT** (backend) | Tokens; refresh opcional; role por tenant. |
| **Deploy** | **Docker + Easypanel** | Um serviço por pasta/Dockerfile; deploy via GitHub. |
| **ORM** | **SQLAlchemy 2** | Modelos, migrações (Alembic); suporte async opcional. |
| **Migrações** | **Alembic** | Versionamento do schema PostgreSQL. |
| **Validação/env** | **Pydantic Settings** | Config e variáveis de ambiente. |

---

## 3. Estrutura do repositório (ordem lógica)

```
massflow/
├── .github/
│   └── workflows/              # (opcional) CI: lint, test
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml ou requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── workers/            # (fase 2) ou lógica no services
│   │   └── ...
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── pages/
│   │   ├── services/
│   │   └── ...
│   └── public/
├── docs/                       # documentação (este doc pode ficar aqui ou na raiz)
├── docker-compose.yml          # desenvolvimento local (backend + frontend + postgres + redis)
├── .env.example
├── README.md
└── MassFlow_VISAO_E_IDEACAO.md
```

- **Backend:** contém apenas a API; não serve o frontend em produção (a menos que se opte por um Dockerfile único).
- **Frontend:** build (e.g. `npm run build`) dentro do Dockerfile; artefato servido por nginx no mesmo container (serviço separado no Easypanel).

---

## 4. Passos de implantação em ordem lógica

### Fase 0 — Preparação (antes do código)

| # | Passo | Detalhes |
|---|--------|----------|
| 0.1 | Criar repositório no GitHub | Nome sugerido: `massflow` ou `MassFlow`. Repo vazio ou com README. |
| 0.2 | Criar projeto no Easypanel | Ex.: "MassFlow". Será o container do projeto. |
| 0.3 | Conectar GitHub ao Easypanel | Conta GitHub vinculada; repositório selecionado; branch (ex.: `main`). |
| 0.4 | Definir serviços no Easypanel | Um serviço por pasta com Dockerfile (ex.: backend, frontend). Banco e Redis como serviços do Easypanel ou externos. |

### Fase 1 — Repositório e estrutura base

| # | Passo | Detalhes |
|---|--------|----------|
| 1.1 | Estrutura de pastas na raiz | Criar `backend/`, `frontend/`, `docs/` (ou manter docs na raiz). |
| 1.2 | Backend: projeto Python | `backend/`: pyproject.toml ou requirements.txt (FastAPI, uvicorn, sqlalchemy, alembic, pydantic-settings, redis opcional). |
| 1.3 | Backend: Dockerfile | `backend/Dockerfile`: estágio build (se precisar de deps de build); estágio final: copiar app, instalar deps, CMD uvicorn. |
| 1.4 | Frontend: projeto React/Vite | `frontend/`: npm create vite@latest . -- --template react-ts; instalar deps (axios, router, etc.). |
| 1.5 | Frontend: Dockerfile | `frontend/Dockerfile`: estágio build (npm ci, npm run build); estágio final: nginx com conteúdo de `dist/`. |
| 1.6 | docker-compose local | `docker-compose.yml` na raiz: backend, frontend (dev ou build), postgres, redis (opcional). |
| 1.7 | .env.example | Listar variáveis: DATABASE_URL, JWT_SECRET, REDIS_URL (opcional), EVOLUTION_*, CORS_ORIGINS, etc. |
| 1.8 | README | Instruções: clone, env, docker-compose up, acessos (backend, frontend). |

### Fase 2 — Backend: base da API e tenant SaaS

| # | Passo | Detalhes |
|---|--------|----------|
| 2.1 | Config e env | `app/config.py` com Pydantic Settings (DATABASE_URL, JWT_*, CORS, Evolution base, URL/API do Agentes SaaS se aplicável). |
| 2.2 | Conexão com PostgreSQL | `app/database.py`: engine, SessionLocal, Base; `get_db()`. |
| 2.3 | Modelos iniciais | Tenant/Organization (com plan_type: 1=só minhas, 2=só plataforma, 3=ambas; credits_balance), User (tenant_id), Lead, List, Tag. |
| 2.4 | Alembic | `alembic init`; primeira migration (create tables). |
| 2.5 | Auth | Registro, login, JWT; `get_current_user`; extrair tenant_id. |
| 2.6 | Rotas base | Health, me; roteadores `/api` (auth, tenants, leads). |
| 2.7 | Multi-tenant | Todas as queries filtradas por tenant_id. |
| 2.8 | Integração Agentes SaaS | Consulta de assinatura (plano ativo) e saldo de créditos; validação antes de campanha; débito ao disparar (ou sync de saldo). |

### Fase 3 — Backend: instâncias e Evolution

| # | Passo | Detalhes |
|---|--------|----------|
| 3.1 | Modelo EvolutionInstance | Por tenant: name, api_url, api_key, display_name, status, limites; **owner** (tenant | platform) para respeitar nível da conta (1, 2 ou 3). |
| 3.2 | Serviço de instâncias | Listar, criar (Evolution API + DB); validar plano (nível 1/2/3) ao criar/editar; health check; rotação (round_robin, least_used). |
| 3.3 | Router instâncias | GET/POST instâncias; POST connect/qr/refresh; manter forma atual de conexão (Evolution). |

### Fase 4 — Backend: campanhas e disparo

| # | Passo | Detalhes |
|---|--------|----------|
| 4.1 | Modelo Campaign | tenant_id, name, type (immediate, scheduled, recurring), list/segment **e filtro por tags**, template (body, variables, spintax), instance_ids (respeitando owner e plano), shield config (delays, batches, limits), status. |
| 4.2 | Modelo CampaignRun / Message | campaign_id, lead_id, message_id (Evolution), status, sent_at; dados para IA integrada (métricas por campanha). |
| 4.3 | Serviço de campanha | Criar, agendar, listar; disparo: buscar leads (lista + tags), **verificar créditos (Agentes SaaS)**, aplicar blindagem, Evolution, registrar envio, **debitar crédito**. |
| 4.4 | Blindagem | Todos os processos e procedimentos (delay aleatório, lotes, pausas, limites, aquecimento, rotação, detecção de risco); configurável por campanha. |
| 4.5 | Router campanhas | CRUD campanhas; POST "run"; listar por funil/tags se aplicável. |
| 4.6 | Fila ou cron | Disparo agendado: APScheduler ou worker Redis; processar scheduled_at <= now. |

### Fase 5 — Backend: webhook Evolution e respostas

| # | Passo | Detalhes |
|---|--------|----------|
| 5.1 | Webhook Evolution | POST /webhook/evolution: receber eventos (messages.update, message.ack, etc.). |
| 5.2 | Associar resposta ao envio/lead | Buscar envio por message_id; atualizar lead (última resposta, status "respondeu"); salvar mensagem recebida no histórico. |
| 5.3 | Webhook/API “aciona IA” | Ao detectar resposta (ou resposta qualificada), chamar webhook/API configurável por tenant com payload (lead_id, campaign_id, text, phone, tags). Agentes de IA conectados assumem a conversa; lead na esteira. |
| 5.4 | Atualizar lead e tags | Status "na_esteira"; opcional aplicar tag (ex.: na-esteira); registrar para IA integrada (análise e sugestão de próximo passo e tagamento — ver Fase 6). |

### Fase 6 — Backend: contatos (manual, CSV, API), tags e integrações

| # | Passo | Detalhes |
|---|--------|----------|
| 6.1 | Contatos manual e CSV | CRUD de leads; import CSV/Excel com mapeamento de colunas; validação e upsert por telefone. |
| 6.2 | API de contatos (push/pull) | POST /api/contacts/sync (push de contatos); GET /api/contacts com filtros (list_id, tags, updated_since); estrutura conforme MassFlow_ESPECIFICACAO_FINAL.md. |
| 6.3 | Tags e funis | Modelo Tag; tags em Lead; segmentação por tag em campanhas; tags automáticas pós-disparo (regras ou IA); relatórios por funil. |
| 6.4 | Modelo Integration | Por tenant: type (webhook, api), url, api_key; eventos (lead.updated, message.sent, response.received, lead.esteira). |
| 6.5 | Eventos para CRM/IA | Chamar webhook/API do cliente e agentes de IA conforme config; debitar créditos (integração Agentes SaaS) ao disparar. |

### Fase 7 — Frontend: base e SaaS

| # | Passo | Detalhes |
|---|--------|----------|
| 7.1 | Login e rota protegida | Página de login; token; rota protegida. |
| 7.2 | Layout e navegação | Menu: Dashboard, Campanhas, Listas/Leads, **Tags/Funis**, Instâncias, **Assinatura/Créditos**, Configurações. |
| 7.3 | API client | Axios baseURL = backend; Bearer; 401. |
| 7.4 | Páginas iniciais | Dashboard; Listas e Leads (manual + import CSV); Instâncias (listar, conectar; respeitar nível da conta); **Assinatura e créditos** (exibir plano e saldo; link para comprar créditos/Agentes SaaS se aplicável). |

### Fase 8 — Frontend: campanhas, tags e IA

| # | Passo | Detalhes |
|---|--------|----------|
| 8.1 | Campanha | Form: nome, tipo, lista, **filtro por tags**, template (variáveis/spintax), instâncias (conforme plano), blindagem. |
| 8.2 | Agendamento | Data/hora e recorrência. |
| 8.3 | Execução e logs | “Rodar agora”; listagem de envios (enviados, entregues, respostas, na esteira); consumo de créditos. |
| 8.4 | Tags e funis | CRUD de tags; aplicar em leads; filtros por tag; relatórios por funil; tags automáticas pós-disparo (config ou sugestão IA). |
| 8.5 | IA integrada | Área “Sugestões da IA”: próximo passo do funil e tagamento pós-disparo; exibir e aplicar com um clique (ou agendar). |
| 8.6 | Webhook/API para agentes de IA | Config por tenant: URL e opções para encaminhar respostas a agentes de IA conectados. |

### Fase 9 — Easypanel: deploy

| # | Passo | Detalhes |
|---|--------|----------|
| 9.1 | Serviço Backend | Novo serviço; origem: GitHub; repositório e branch; **Build context: pasta `backend/`**; Dockerfile em `backend/Dockerfile`. Variáveis de ambiente (DATABASE_URL, JWT_SECRET, etc.). Porta 8000. |
| 9.2 | Serviço Frontend | Novo serviço; origem: GitHub; **Build context: pasta `frontend/`**; Dockerfile em `frontend/Dockerfile`. Porta 80 (nginx). |
| 9.3 | PostgreSQL | Serviço de banco no Easypanel ou conexão a DB externo; passar DATABASE_URL ao backend. |
| 9.4 | Redis (quando houver worker) | Serviço Redis; REDIS_URL no backend/worker. |
| 9.5 | Domínios e rede | Domínio ou subdomínio para API (ex.: api.massflow.xxx) e para frontend (ex.: app.massflow.xxx); backend acessível pelo frontend (CORS). |
| 9.6 | Webhook Evolution | URL pública do backend (ex.: https://api.massflow.xxx/webhook/evolution) configurada na Evolution API. |

---

## 5. Detalhamento dos Dockerfiles

### 5.1 Backend (`backend/Dockerfile`)

```dockerfile
# Exemplo enxuto
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- No Easypanel: **Build context** = pasta `backend/` (ou caminho que contém o Dockerfile).
- `.dockerignore` em `backend/`: `__pycache__`, `.env`, `*.pyc`, `.git`, `tests`, `alembic/versions/*.py` (ou incluir versões se quiser rodar migrate no deploy).

### 5.2 Frontend (`frontend/Dockerfile`)

```dockerfile
# Estágio 1: build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Estágio 2: servir com nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf  # SPA fallback para index.html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- **Build context** no Easypanel = pasta `frontend/`.
- `frontend/nginx.conf`: `try_files $uri $uri/ /index.html;` para rotas do React Router.

---

## 6. Variáveis de ambiente (exemplo)

### Backend

```env
DATABASE_URL=postgresql://user:pass@host:5432/massflow
JWT_SECRET=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080
CORS_ORIGINS=https://app.massflow.xxx,http://localhost:5173
EVOLUTION_API_URL=https://...
EVOLUTION_API_KEY=...
REDIS_URL=redis://redis:6379/0
```

### Frontend (build time, se necessário)

```env
VITE_API_URL=https://api.massflow.xxx
```

---

## 7. Ordem resumida para começar o código

1. Criar repo GitHub + projeto Easypanel e conexão (Fase 0).
2. Criar pastas `backend/` e `frontend/` com projetos base e Dockerfiles (Fase 1).
3. Subir backend: config, DB, modelos iniciais, auth, multi-tenant (Fase 2).
4. Instâncias Evolution (Fase 3).
5. Campanhas e disparo com blindagem (Fase 4).
6. Webhook Evolution + resposta → webhook IA + esteira (Fase 5).
7. Integrações CRM e leads (Fase 6).
8. Frontend: login, layout, listas, instâncias, campanhas (Fases 7 e 8).
9. Configurar serviços no Easypanel (Fase 9).

**Local de implantação:** pasta raiz **Projetos-FabriaIA**; código do MassFlow em **MassFlow/**; integração com projeto **Agentes SaaS** (assinatura e créditos) no mesmo ecossistema. Com isso, a implantação fica organizada: **um serviço por pasta com Dockerfile**, tecnologias definidas, passos em ordem lógica e requisitos alinhados à **MassFlow_ESPECIFICACAO_FINAL.md**.
