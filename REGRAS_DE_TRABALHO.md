# MassFlow — Regras de Trabalho

Regras definidas para o desenvolvimento e implantação do projeto.

---

## 1. Repositório e deploy

- **Repositório GitHub:** https://github.com/ftsmazzo/massflow
- **Easypanel:** 2 serviços via Dockerfile:
  - **Backend:** build a partir de `backend/Dockerfile` (contexto: pasta `backend/`)
  - **Frontend:** build a partir de `frontend/Dockerfile` (contexto: pasta `frontend/`). **Obrigatório:** definir **Build Arg** `VITE_API_URL` = URL do backend (ex: `https://...-backend....easypanel.host`), senão o front chama o próprio domínio e retorna 405.
- **Banco de dados:** PostgreSQL no mesmo projeto Easypanel; banco `massflow` já criado. URL de conexão **interna** (entre serviços): fornecida nas variáveis de ambiente.

---

## 2. Variáveis de ambiente

- **Arquivo `.env`** fica **apenas local**: contém todas as variáveis já organizadas para copiar e colar no Easypanel (podem ser as variáveis reais). **Não é commitado** (está no `.gitignore`).
- **Arquivo `.env.example`** é commitado: lista as variáveis com valores de exemplo/placeholders, sem segredos reais.
- Em outra VPS ou ambiente: basta **alterar as variáveis** no Easypanel (ou no `.env` local e refazer o deploy); nenhuma configuração manual de banco ou shell é necessária.

---

## 3. Banco de dados e implantação

- **Tudo relacionado ao banco** (criação de banco, tabelas, migrações, atualizações) ocorre **na implantação no Easypanel**, ao subir o backend.
- **Nada via shell ou bash** para o banco: o backend, ao iniciar, executa as migrações (ex.: `alembic upgrade head`) ou a criação inicial das tabelas, de forma automática.
- Assim, ao fazer deploy em outra VPS, basta configurar a nova `DATABASE_URL` (e demais variáveis); o container ao subir aplica o schema necessário.

---

## 4. Fluxo de trabalho (commit e push)

- **Sempre que** for editado ou criado algo no projeto, deve ser feito **commit e push** no repositório GitHub.
- Em seguida, a **implantação/atualização no Easypanel** fica a cargo do usuário (redeploy a partir do repositório).
- Resumo: **editar/criar → commit → push → (você) deploy no Easypanel**.

---

## 5. Resumo

| Item | Regra |
|------|--------|
| Repo | https://github.com/ftsmazzo/massflow |
| Serviços Easypanel | Backend (backend/Dockerfile), Frontend (frontend/Dockerfile) |
| Banco | PostgreSQL no projeto; URL interna via variável de ambiente |
| .env | Só local; variáveis reais organizadas; não commitado |
| .env.example | Commitado; placeholders; referência |
| Banco / migrações | Tudo na implantação (backend sobe e aplica); nada manual em shell |
| Código | Após editar/criar → commit + push → deploy no Easypanel |
