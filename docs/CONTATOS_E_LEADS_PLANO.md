# Contatos e Leads — Plano e passos

Documento que consolida o que foi projetado, a distinção **contatos físicos** vs **leads em campanhas/funil**, e os passos de implementação (incluindo API para sistemas externos consumirem contatos).

---

## 1. Conceito: contatos físicos vs leads em campanhas/funil

### 1.1 Contatos físicos (base)

- **Um contato físico** = uma pessoa identificada por **telefone** (único por tenant).
- Dados: telefone (obrigatório), nome, email, campos custom (JSON), opt-in, status (ativo, na_esteira, opt_out).
- No modelo atual do MassFlow essa entidade é a tabela **`leads`** (Lead). Ou seja: **Lead = contato físico**. Na API e na UI podemos expor como **"Contatos"** para clareza; no banco permanece `leads`.
- Um mesmo contato (telefone) não se repete por tenant: é criado/atualizado (upsert) por telefone.

### 1.2 Listas

- **Lista** = agrupamento nomeado de contatos (ex.: "Base Black Friday", "Inscritos site").
- Relação N:N: um **contato** pode estar em **várias listas**; uma **lista** tem **vários contatos** (tabela `list_leads`).
- Listas são usadas para organizar bases e, depois, para **escolher o público de uma campanha** (campanha “usa” uma lista ou segmento por tags).

### 1.3 Leads em campanhas / funil

- **“Lead” em campanha/funil** = o **mesmo contato físico** (Lead) quando:
  - está em **listas** usadas por campanhas, e
  - passa a ter **histórico de disparos** (recebeu campanha X, respondeu, entrou na esteira) e **tags** para funil.
- **Tags** (por tenant) ficam no **contato** (Lead): ex. `quente`, `interessado`, `na-esteira`, `funil-vendas-2025`. Servem para:
  - **Segmentação** em campanhas (enviar só para quem tem tag X ou não tem Y).
  - **Funil:** etapas e relatórios (etapa-1, etapa-2, concluído).
- Quando existir o modelo **Campaign**, o vínculo “contato recebeu campanha” será registrado em tabela de envios (ex.: `campaign_messages` ou `campaign_recipients`: campaign_id, lead_id, sent_at, status). Não é necessário outra tabela “lead em campanha”: o contato (Lead) + lista + tags + histórico de envios/respostas formam o “lead em campanha/funil”.

### 1.4 Resumo do modelo atual (sem mudar estrutura)

| Conceito na conversa      | No sistema MassFlow                         |
|---------------------------|---------------------------------------------|
| Contato físico            | **Lead** (tabela `leads`: phone, name, email, opt_in, status, custom_fields) |
| Contato em listas         | Lead + associação em **List** (tabela `list_leads`) |
| Lead em campanha / funil  | Mesmo Lead + **tags** + histórico de envios (quando houver Campaign) |
| Tags para funis           | **Tag** (tabela `tags`) + `lead_tags` (N:N com Lead) |

Não é obrigatório criar tabela “Contact” separada: Lead já é o contato físico; listas e tags organizam o uso em campanhas e funis.

---

## 2. API para sistemas externos (consumir e enviar contatos)

Objetivo: outros sistemas (CRM, site, Agentes SaaS, etc.) **conversarem com o MassFlow** via API para enviar e receber contatos.

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

1. **Backend:** routers de **contacts** (CRUD + GET com filtros para pull) e **lists** (CRUD + add/remove contacts) e **tags** (CRUD + aplicar em contatos); em seguida **POST /api/contacts/sync** para push.
2. **Frontend:** página **Contatos** (listar, criar, editar, filtros por lista/tag); página **Listas** (CRUD, ver contatos da lista, adicionar/remover); **Tags** (CRUD, aplicar em massa na tela de contatos); **Import CSV** (mapeamento + import).
3. **Documentação:** exemplo de uso da API (GET /api/contacts e POST /api/contacts/sync) para sistemas externos consumirem e enviarem contatos.

Com isso, os contatos ficam bem definidos (contatos físicos = Lead; listas e tags para funis e campanhas), e a API permite que seus outros sistemas conversem com o MassFlow para consumir e enviar contatos. Depois entram campanhas e disparo usando essas listas e tags.
