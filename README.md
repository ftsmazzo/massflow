# MassFlow

Sistema de **disparos em massa** via Evolution API — captação de leads, campanhas, tags/funis, blindagem anti-ban e integração com agentes de IA.

## Documentação

- **MassFlow_ESPECIFICACAO_FINAL.md** — Requisitos completos (tags, IA, contatos, SaaS 3 níveis, créditos, Agentes SaaS).
- **MassFlow_VISAO_E_IDEACAO.md** — Visão e pilares do produto.
- **MassFlow_DOCUMENTO_IMPLANTACAO.md** — Passos de implantação (fases 0–9) e tecnologias.

## Estrutura

```
MassFlow/
├── backend/          # API FastAPI (Python)
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/         # SPA React + Vite + TypeScript
│   ├── src/
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── .env.example
└── README.md
```

## Desenvolvimento local

### Pré-requisitos

- Docker e Docker Compose (ou Node 20 + Python 3.11 + PostgreSQL 15 para rodar sem Docker).

### Com Docker

1. Copie o ambiente:
   ```bash
   cp .env.example .env
   ```
2. Suba os serviços:
   ```bash
   docker compose up -d
   ```
3. Acesse:
   - **Frontend:** http://localhost
   - **Backend API:** http://localhost:8000
   - **Health:** http://localhost:8000/health
   - **Docs (quando disponível):** http://localhost:8000/docs

### Sem Docker (dev)

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
# Crie o banco massflow no PostgreSQL e configure DATABASE_URL no .env
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Acesse http://localhost:5173 (proxy para API em :8000).

## Deploy (Easypanel + GitHub)

1. Repositório no GitHub com esta estrutura.
2. Projeto no Easypanel; conectar repositório.
3. **Serviço Backend:** build context = pasta `backend/`, Dockerfile em `backend/Dockerfile`; porta 8000; variáveis de ambiente (DATABASE_URL, JWT_SECRET, etc.).
4. **Serviço Frontend:** build context = pasta `frontend/`, Dockerfile em `frontend/Dockerfile`; porta 80.
5. **PostgreSQL:** serviço no Easypanel ou conexão externa; passar DATABASE_URL ao backend.

## Regras de trabalho

Ver **REGRAS_DE_TRABALHO.md** (repositório, Easypanel, .env local, banco na implantação, commit + push).

## Licença

Projeto interno — Projetos-FabriaIA.
