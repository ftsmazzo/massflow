# MassFlow — Regras de Trabalho

Regras definidas para o desenvolvimento e implantação do projeto.

---

## 1. Repositório e deploy

- **Repositório GitHub:** https://github.com/ftsmazzo/massflow
- **Easypanel:** 2 serviços via Dockerfile:
  - **Backend:** build a partir de `backend/Dockerfile` (contexto: pasta `backend/`). Health check: GET `/` ou GET `/health` na porta 8000 (Easypanel deve usar um deles para marcar o serviço como healthy).
  - **Frontend:** build a partir de `frontend/Dockerfile` (contexto: pasta `frontend/`). **Em produção:** não definir `VITE_API_URL` no build; no **container** definir **BACKEND_URL** = `http://nome-do-servico-backend:8000`. O nginx do front faz proxy de `/api` para o backend (mesma origem = sem CORS).
- **Banco de dados:** PostgreSQL no mesmo projeto Easypanel; banco `massflow` já criado. URL de conexão **interna** (entre serviços): fornecida nas variáveis de ambiente.

---

## 2. Variáveis de ambiente

- **Arquivo `.env`** fica **apenas local**: contém todas as variáveis já organizadas para copiar e colar no Easypanel (podem ser as variáveis reais). **Não é commitado** (está no `.gitignore`).
- **Arquivo `.env.example`** é commitado: lista as variáveis com valores de exemplo/placeholders, sem segredos reais.
- Em outra VPS ou ambiente: basta **alterar as variáveis** no Easypanel (ou no `.env` local e refazer o deploy); nenhuma configuração manual de banco ou shell é necessária.

### CORS no backend (Easypanel)

- **CORS_ORIGINS**: use **uma única URL** = a URL do frontend tal qual o usuário acessa no navegador.
  - Exemplo: `https://fabricaia-massflow-frontend.iei9vc.easypanel.host`
  - **Sem** barra no final, **sem** `https://` duplicado.
- Não é obrigatório preencher **CORS_ORIGIN_REGEX**; se quiser, pode deixar vazio (o backend usa um padrão para `*.easypanel.host`).

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
