# Contatos e Leads — Plano e passos

Documento que consolida o que foi projetado, a **ordem correta do fluxo** (campanha → contatos) e os passos de implementação.

---

## 1. Decisão de produto: contatos entram pela campanha

**Regra central:** contatos não entram no sistema de forma solta (import em massa sem campanha, “conexão de CRM” para trazer base inteira). A entrada é **sempre atrelada a uma ação de marketing**.

### 1.1 Fluxo correto (campanha-first)

1. **Criar campanha** para uma ação (ex.: Black Friday, lançamento).
2. **Na criação da campanha**, definir os **alvos** do disparo:
   - **Importação CSV** (upload naquela campanha, contatos entram para uma lista);
   - Ou escolher uma **lista interna** já existente (leads que vieram de campanhas anteriores, filtrados por tags).
   - *(Conexão API externa — CRM, etc. — fica fora do escopo por enquanto.)*
3. **Disparo:** enviamos para esses alvos; para cada um registramos **recebeu / leu / respondeu / chegou ao contato com IA**.
4. **A cada passo do funil** agregamos **tags** (ex.: `recebeu`, `leu`, `respondeu`, `na-esteira`).
5. Esses alvos passam a ser **leads/contatos do sistema** (tabela `leads` com tags e histórico). A partir daí:
   - Montamos **novas listas de disparo** com **filtros por tag** para as próximas campanhas.
   - Não precisamos “importar contatos” de novo sem campanha: quem entra na base é quem já foi alvo de alguma campanha (ou foi carregado como alvo ao criar uma campanha).

### 1.2 O que NÃO fazemos (evitar no desenvolvimento)

- **Não:** tela “Importar contatos” ou “Conectar CRM” como ação independente, populando base de contatos sem campanha ativa.
- **Não:** “conexão de contatos remota” que puxa toda a base do CRM para o MassFlow fora do contexto de uma campanha.
- **Sim:** “Ao criar campanha → carregar alvos” (por enquanto só **importação CSV** e lista interna por tags; conexão API externa fora do escopo). Os contatos passam a existir no sistema como resultado do uso em campanha e do funil (tags).

### 1.3 Conceito no sistema (após a decisão acima)

- **Lead** = contato físico no MassFlow (telefone único por tenant). Existe na base **porque** foi alvo de alguma campanha (ou foi carregado como alvo ao criar uma) e tem histórico/tags.
- **Tags** (por tenant) no lead: ex. `recebeu`, `respondeu`, `na-esteira`, `quente`. Servem para **segmentação** nas próximas campanhas (enviar só para quem tem tag X) e para funil.
- **Listas** = agrupamentos de leads (N:N). Usadas para organizar e para escolher público em **novas** campanhas; listas podem ser construídas por **filtro de tags** sobre os leads já existentes.
- **Campanha** = ação de disparo com alvos definidos na criação (carregados de API/CSV ou lista interna); tracking (recebeu/leu/respondeu/IA) e aplicação de tags; os alvos viram (ou atualizam) leads no sistema.

### 1.4 Resumo (sem mudar estrutura de banco)

| Conceito                | No MassFlow |
|-------------------------|-------------|
| Contato físico / lead  | **Lead** (tabela `leads`). Entra na base via campanha (alvos da campanha). |
| Listas                  | **List** + `list_leads`. Agrupamentos para próximas campanhas; podem ser por filtro de tags. |
| Tags                    | **Tag** + `lead_tags`. Agregadas ao longo do funil (recebeu, leu, respondeu, na-esteira). |
| Campanha                | **Campaign** + tabela de envios. Alvos carregados na criação (API/CSV/lista). |

---

## 2. API para sistemas externos (consumir e enviar contatos)

**Contexto (campanha-first):** A API de push (sync) é usada quando o cliente **carrega alvos na criação de uma campanha** a partir de um sistema externo (CRM, etc.). O pull (GET) serve para que sistemas externos consultem os leads que já estão no MassFlow (após campanhas). Não usamos a API para “importar base inteira” sem campanha.

Objetivo: outros sistemas (CRM, site, Agentes SaaS, etc.) **conversarem com o MassFlow** via API para enviar e receber contatos **no contexto de campanhas e listas derivadas**.

### 2.1 Enviar contatos para o MassFlow (push)

- **POST /api/contacts/sync** (ou `/api/contacts/import`)
- **Body:** array de contatos, cada um com:
  - `phone` (obrigatório)
  - `name`, `email` (opcional)
  - `tags` (opcional): array de nomes de tags (criar se não existir; associar ao lead)
  - `custom_fields` (opcional): objeto chave-valor
  - `list_id` ou `list_slug` (opcional): incluir o contato nessa lista
  - `opt_in` (opcional, default true)
- **Regra:** upsert por `(tenant_id, phone)`: se já existir, atualiza; senão, cria.
- **Resposta:** `{ created: number, updated: number, errors: [] }` (e detalhes de erros por linha, se necessário).

### 2.2 Receber contatos do MassFlow (pull / consumir)

- **GET /api/contacts**
  - Query params: `list_id`, `tags` (ex.: `tags=quente,interessado`), `updated_since` (ISO datetime), `opt_in` (true/false), `status`, paginação (`limit`, `offset` ou `page`, `per_page`).
  - Resposta: array de contatos (leads) com: `id`, `phone`, `name`, `email`, `tags[]`, `custom_fields`, `opt_in`, `status`, `last_sent_at`, `last_response_at`, `list_ids[]` (listas em que está), `created_at`, `updated_at`.
- Sistemas externos usam esse GET para **consumir** contatos (sincronizar, relatórios, etc.).

### 2.3 Autenticação da API

- Endpoints de contatos exigem **JWT** (tenant identificado pelo token), como o resto da API.
- Para integração máquina a máquina: o sistema externo usa um usuário (ou “API key” futura) do tenant e envia Bearer token.

---

## 3. Passos de implementação (ordem sugerida)

### Fase A — Backend: contatos e listas (API interna + API para externos)

| # | Passo | Detalhe |
|---|--------|--------|
| A.1 | Router **Contacts** (`/api/contacts`) | GET list (filtros: list_id, tags, updated_since, status, opt_in; paginação); GET by id; POST create (upsert por phone); PATCH update; DELETE (soft ou hard). Schemas Pydantic request/response. |
| A.2 | Router **Lists** (`/api/lists`) | GET list; GET by id (com contatos da lista); POST create; PATCH update; DELETE. POST/DELETE `/api/lists/{id}/contacts` (add/remove contact_ids). |
| A.3 | Router **Tags** (`/api/tags`) | GET list; POST create; PATCH; DELETE. POST `/api/tags/{id}/apply` ou `/api/contacts/bulk-tag` (aplicar tag a N contact_ids). |
| A.4 | **POST /api/contacts/sync** | Payload: array de contatos (phone, name, email, tags[], list_id, custom_fields, opt_in). Upsert por phone; criar tags se não existir; associar a lista se informada. Resposta: created, updated, errors. |
| A.5 | **GET /api/contacts** (pull) | Garantir query params: list_id, tags, updated_since, status, opt_in, limit, offset. Resposta incluir tags (nomes), list_ids, last_sent_at, last_response_at. Documentar para sistemas externos. |

### Fase B — Frontend: contatos (UI)

| # | Passo | Detalhe |
|---|--------|--------|
| B.1 | Página **Contatos** | Listar contatos (tabela/cards); filtros por lista, tag, status; busca por nome/telefone; paginação. |
| B.2 | Criar/editar contato | Modal ou página: telefone, nome, email, opt-in, status; tags (multiselect); listas (multiselect ou “adicionar à lista”). |
| B.3 | Importação CSV | Upload CSV; mapeamento de colunas (telefone obrigatório; nome, email, tags, listas opcionais); preview; import (chamar sync ou endpoint dedicado); relatório de sucesso/erros. |
| B.4 | Página **Listas** | CRUD listas; ao abrir uma lista, listar contatos dessa lista; “Adicionar contatos” (busca ou seleção); “Remover da lista”. |
| B.5 | Gestão de **Tags** | Listar tags; criar/editar/excluir; “Aplicar em massa” (selecionar contatos e aplicar tag). Em Contatos, filtro e exibição de tags por contato. |

### Fase C — Campanhas e “lead em campanha” (depois)

| # | Passo | Detalhe |
|---|--------|--------|
| C.1 | Modelo **Campaign** | tenant_id, name, type, list_id (ou segmento por tags), template, instance_ids, shielding_ref, status, scheduled_at, etc. |
| C.2 | Tabela de envios | Ex.: `campaign_messages` (campaign_id, lead_id, sent_at, message_id Evolution, status). Contato (Lead) “registrado em campanha” = registro nessa tabela + tags atualizadas. |
| C.3 | Disparo com blindagem | Serviço que lê config de blindagem, monta fila de leads (lista + filtro tags), aplica delays/lotes/limites e envia via Evolution; atualiza last_sent_at, campaign_messages, créditos. |

---

## 4. Ordem prática para “lidar com os contatos” agora

1. **Campanhas primeiro:** Ao criar campanha, o usuário define os **alvos** (carregar de API externa, CSV ou lista interna por tags). Não há “importar contatos” ou “conectar CRM” como tela independente.
2. **Backend:** routers **contacts**, **lists**, **tags**; **POST /api/contacts/sync** usado quando a campanha carrega alvos de sistema externo ou CSV; GET /contacts para pull por sistemas externos e para listas/filtros internos.
3. **Frontend:** **Contatos** = listar/editar os leads que já existem no sistema (oriundos de campanhas). **Listas** = agrupamentos para próximas campanhas (filtro por tags). **Tags** = gestão e aplicação em massa. **Import CSV** = no contexto de **criação/edição de campanha** (upload de alvos daquela campanha), não como ação solta.
4. **Documentação:** API (GET/POST contacts) para sistemas externos, sempre no contexto “alvos de campanha” e “listas derivadas de leads com tags”.

Com isso, o desenvolvimento evita desvio para “base de contatos solta”; contatos entram pela campanha e, com tags, viram base para novas listas e campanhas.
