# Frontend + Backend no Easypanel (MassFlow) – sem CORS

## Estratégia: proxy no frontend

O frontend usa **proxy no nginx**: o navegador chama `/api/...` no próprio domínio do front; o nginx repassa para o backend. **Não há requisição cross-origin**, então **não há CORS**.

### Configuração no Easypanel

**1. Frontend (massflow-frontend)**

- **Build:** não defina `VITE_API_URL` (deixe em branco).
- **Variáveis de ambiente do container (runtime):**
  - **BACKEND_URL** = `http://NOME_DO_SERVICO_BACKEND:8000`  
    Exemplo: `http://fabricaia-massflow-backend:8000`  
    (use o nome interno do serviço do backend no Easypanel e a porta 8000).

**2. Backend**

- Porta **8000** (já é o padrão).
- CORS deixa de ser necessário para o front; pode manter `CORS_ORIGINS` se quiser usar a API de outro domínio (ex.: Swagger).

### Fluxo

1. Usuário acessa `https://fabricaia-massflow-frontend.iei9vc.easypanel.host`
2. O front chama `POST /api/auth/register` (mesma origem).
3. O nginx do front recebe e faz proxy para `http://fabricaia-massflow-backend:8000/api/auth/register`.
4. O backend responde; o nginx devolve a resposta ao navegador. Sem CORS.
