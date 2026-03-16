# MassFlow — Visão e Ideação (Versão Final)

Documento de concepção da **versão final do MassFlow**. Para requisitos detalhados (tags/funis, IA integrada, fontes de contatos, modelo SaaS com 3 níveis e créditos, integração Agentes SaaS), ver **MassFlow_ESPECIFICACAO_FINAL.md**.

---

## 1. Posicionamento

- **O que é:** MassFlow = plataforma de **disparos em massa** via API não oficial (Evolution), voltada a **captação de leads** e **campanhas**. Controle de leads, respostas vinculadas aos envios, webhook que aciona **IA para assumir a conversa** (tirando o lead do fluxo do disparo e colocando na esteira) e integração com CRM.
- **O que não é:** O **projeto Devocional fica de fora** — é outro produto. MassFlow é **apenas** o disparador para captação de leads e campanhas, sem lógica de devocional.
- **Diferenciais desejados:** Moderna, diferente, poderosa; blindagem de primeira linha; respostas que acionam IA no lugar do número do disparo e levam o lead para a esteira; integração dinâmica com CRM/leads; multi-cliente com conta própria e personalização.

---

## 2. Problemas atuais (a superar)

- Listas, contatos, agendamentos, logs e controle de leads **precários** no cenário atual.
- Respostas aos disparos existem de forma **simples** no MassFlow atual — falta **aperfeiçoar**: ao responder (ex.: “Eu quero”), acionar uma **IA que assume a conversa no lugar do número do disparo** e coloca o lead na **esteira** (fluxo de conversa/qualificação), em vez de só notificar ou fazer auto-resposta fixa.
- Falta **multi-cliente**: cada cliente com sua conta, suas listas, suas instâncias (ou compartilhamento controlado), seus leads e seu CRM.
- Blindagem pode ser **reforçada** com práticas das ferramentas pesquisadas (Wasender, MultiSender, SuperSender) e boas práticas anti-ban.
- Falta **diversificação de mensagens** (spintax, variáveis, templates) e outras práticas eficientes de mercado.

---

## 3. Pilares da versão final

### 3.1 Multi-tenant e conta do cliente

- **Cliente cria conta** (registro/login). Modelo SaaS com **3 níveis de conta** (só minhas instâncias / só da plataforma / ambas) e **créditos avulsos**; integração com **Agentes SaaS** para assinatura e créditos (detalhes em MassFlow_ESPECIFICACAO_FINAL.md).
- Cada cliente tem:
  - **Organização/Workspace** (se no futuro houver equipes, pode ter mais de um por conta).
  - **Contatos/Listas** próprias: inclusão **manual**, **importação CSV** e **consumo via API** (estrutura em MassFlow_ESPECIFICACAO_FINAL.md).
  - **Tags** para funis efetivos (segmentação, tags automáticas pós-disparo, relatórios por funil).
  - **Instâncias WhatsApp** conforme nível da conta (próprias, da plataforma ou ambas).
  - **Campanhas** (disparos agendados ou imediatos).
  - **Leads** (contatos enriquecidos com histórico, tags, respostas, campos custom).
  - **Logs, métricas e relatórios** por campanha, lead e funil.
- **Personalização e individualização:** configurações por cliente (horários, limites, templates, variáveis, integrações, webhook/API para IA).

### 3.2 Disparos em massa (core)

- **Campanhas:** nome, tipo (disparo único, agendado, recorrente), lista(s) ou segmento, template de mensagem, regras de blindagem.
- **Conteúdo:**
  - **Variáveis:** `{nome}`, `{telefone}`, `{email}`, campos custom do lead (ex.: `{empresa}`, `{cidade}`).
  - **Diversificação de mensagens:** spintax (ex.: `{Olá|Oi|Bom dia}`), múltiplas variações por campanha (sorteio ou rotação), templates com alternativas.
  - Suporte a **texto, imagem, áudio, vídeo, documento, PDF** (Evolution API).
- **Agendamento:** data/hora (timezone do cliente), repetição (diária, semanal), filas por instância.
- **Seleção de instâncias:** por campanha — uma instância fixa, ou rotação entre N instâncias do cliente (round-robin, least_used, por tag de lead).
- **Regras de envio:** só para contatos com WhatsApp ativo (validação), só opt-in (consentimento), filtro por tag/segmento, limite por lead (ex.: 1 envio/dia por campanha).

### 3.3 Blindagem (reforçada)

Objetivo: **evitar ou mitigar ao máximo** bloqueios e quedas.

- **Delays:**
  - Intervalo **aleatório** entre mensagens (ex.: min–max em segundos), nunca fixo.
  - Variação por tipo de conta (nova vs madura) e por horário (evitar picos).
- **Lotes e pausas:**
  - Envio em **lotes** (ex.: 15–30 mensagens) com **pausa** entre lotes (ex.: 10–15 min).
  - “Pausa longa” configurável após X mensagens (ex.: 50 msg → pausa 15–30 min).
- **Limites por instância e por conta:**
  - Limite/hora e limite/dia **por instância** (e, se aplicável, por cliente).
  - Perfis de “idade” da conta: novo / estabelecido / maduro (com limites progressivos).
- **Aquecimento (warm-up):**
  - Período de **aquecimento** para instâncias novas: só envios leves (ex.: 10–20/dia) por N dias antes de liberar disparo em massa.
- **Rotação de instâncias:**
  - Troca automática de instância após X mensagens ou ao atingir limite horário/diário (evitar sobrecarga em um único número).
- **Detecção de risco:**
  - Monitorar erros 403/429 e padrões de falha; marcar instância como “em risco” ou “pausada” e parar envios até revisão.
- **Conteúdo:**
  - Alertas para mensagens muito repetidas (ex.: > 70% iguais); sugestão de uso de variáveis/spintax.
  - Opção de “descadastro” em campanhas (link ou palavra-chave).
- **Consentimento e lista limpa:**
  - Flag de opt-in por lead; exclusão ou desativação de quem pediu para sair; limpeza periódica de inativos (não lidos/não respondidos por X dias).

### 3.4 Respostas conectadas aos disparos — Webhook que aciona IA e leva o lead para a esteira

- **Vínculo disparo ↔ resposta:**
  - Cada envio (mensagem saída) tem ID único (ex.: `message_id` da Evolution).
  - Respostas recebidas (webhook Evolution) são **associadas** ao último envio daquele contato (ou à thread/conversa).
  - Manter **thread de conversa** por lead: sequência de envios + respostas ordenadas no tempo.
- **Webhook que dispara a IA (fluxo principal):**
  - Quando o lead **responde** (ex.: “Eu quero”, “Quero saber mais”), o MassFlow dispara um **webhook** para um sistema externo.
  - Esse webhook **aciona uma IA** que **passa a interagir com o usuário no lugar do outro número** — ou seja, a IA “chama” ou responde **a partir do número dela** (ou de um número dedicado da esteira) e **inicia uma conversa** com o lead.
  - Efeito: o lead **sai do fluxo do disparo** (campanha em massa) e **entra na esteira** (pipeline de conversa/qualificação), onde a IA (ou um atendente) continua o diálogo.
  - O MassFlow registra que o lead foi “transferido para a esteira” (status do lead atualizado; opcionalmente notifica CRM).
- **Regras de negócio:**
  - Atualizar lead: última resposta, última data de interação, status (ex.: “respondeu”, “na esteira”, “não respondeu”, “opt-out”).
  - Contadores: total de envios, total de respostas, leads que entraram na esteira, taxa por campanha.
- **Integração com fluxos externos:**
  - **Webhook ou API** para encaminhar respostas a **agentes de IA conectados**; payload (lead_id, campaign_id, texto, telefone, tags). Sistema externo aciona a IA e coloca o lead na esteira.
  - **IA integrada:** analisa disparos e **sugere próximo passo do funil** e **tagamento pós-disparo** (detalhes em MassFlow_ESPECIFICACAO_FINAL.md).
  - Opcional: notificar CRM com “lead entrou na esteira”.

### 3.5 Integração dinâmica com CRM e banco de leads

- **Banco de leads interno (MassFlow):**
  - Por cliente: tabela de **leads** com telefone (único por cliente), nome, email, campos custom (JSON ou colunas configuráveis), tags, opt_in, última_interação, última_resposta, etc.
  - Histórico de **mensagens** (envio + recebimento) vinculado ao lead e à campanha.
- **Conexão com CRM externo (dinâmica):**
  - **Opção A — API do cliente:** cliente informa URL + API key (ou OAuth); MassFlow envia eventos (novo lead, envio, resposta, opt-out) e/ou sincroniza listas (pull/push).
  - **Opção B — Webhooks do MassFlow:** cliente configura URL de webhook; MassFlow dispara “lead.atualizado”, “mensagem.enviada”, “resposta.recebida”, “lead.optout”.
  - **Opção C — Importação/exportação:** CSV/Excel de leads; export de histórico de conversas e métricas para o cliente usar no CRM dele.
  - **Mapeamento de campos:** cliente define quais campos do lead (MassFlow) mapeiam para quais campos do CRM (ex.: telefone → phone, nome → name, tag → stage).
- **Uso em campanhas:**
  - Variáveis de mensagem podem vir do **lead interno** ou (se configurado) do **CRM externo** (via cache ou consulta em tempo de envio).
  - Segmentação: “enviar só para leads com tag X” ou “com campo Y preenchido”.

### 3.6 Diversificação de mensagens e boas práticas

- **Spintax:** sintaxe no texto, ex.: `{Olá|Oi|Bom dia}, {nome}!` → uma variação escolhida por envio (aleatória ou rotativa).
- **Múltiplas versões de template:** campanha com 3–5 textos alternativos; a cada envio escolhe um (aleatório ou por lead_id para consistência).
- **Variáveis obrigatórias:** sempre que possível usar pelo menos `{nome}` (e outros do lead) para reduzir repetição e aumentar sensação de personalização.
- **Validação de números:** antes de campanha, opção de “validar” lista (consultar se número tem WhatsApp) e marcar lead como ativo/inativo.
- **Horário de envio:** janelas configuráveis por cliente (ex.: 9h–18h) para não enviar de madrugada; respeitar timezone.
- **Relatórios:** por campanha — enviados, entregues, lidos, respostas, opt-outs, falhas; por lead — última atividade, status; exportação para análise.

---

## 4. Arquitetura de alto nível (ideação)

- **Frontend:** SPA moderna (ex.: React/Vite) com login, dashboard por cliente, gestão de listas/leads, campanhas, agendamentos, logs, respostas e configurações de integração (webhook, API, mapeamento).
- **Backend:** API (ex.: FastAPI) multi-tenant (tenant_id = organização do cliente em todas as tabelas).
  - **Auth:** registro, login, JWT; recuperação de senha; roles (admin plataforma vs cliente).
  - **Tenants/Organizações:** cadastro de cliente, plano (limites de envio, de instâncias, de leads).
  - **Instâncias:** por tenant; criação/conexão Evolution; health check; rotação e limites (blindagem).
  - **Leads/Contatos:** CRUD por tenant; listas/tags; import CSV/Excel; campos custom; opt-in; histórico de mensagens.
  - **Campanhas:** CRUD; tipo (único, agendado, recorrente); conteúdo (template + variáveis + spintax); seleção de lista/segmento e de instâncias; regras de blindagem (delays, lotes, pausas, limites).
  - **Disparo:** fila de envio (worker/cron); aplicação de blindagem; registro de cada mensagem (message_id, lead_id, campaign_id); atualização de lead (last_sent, counts).
  - **Webhook Evolution:** receber eventos (entregas, leituras, **respostas**); associar resposta ao envio/lead; atualizar lead e histórico; **disparar webhook que aciona a IA** (sistema externo assume a conversa e coloca o lead na esteira); opcionalmente notificar CRM.
  - **Integrações:** tabela de “conexões” por tenant (tipo: webhook, API CRM); mapeamento de campos; envio de eventos (lead, envio, resposta, opt-out).
- **Banco de dados:** PostgreSQL (ou equivalente) com schemas ou tenant_id em tabelas; filas (ex.: Redis) para processamento assíncrono de campanhas e envios.
- **Evolution API:** mantida como canal de envio/recebimento; instâncias podem ser “do cliente” (cada um conecta a sua) ou pool gerenciado pela plataforma com cotas por tenant.

---

## 5. Roadmap em fases (sugestão)

1. **Fase 1 — Base multi-tenant e leads**
   - Conta do cliente (registro/login), organização, leads e listas, campos custom, opt-in.
   - Campanha simples: disparo imediato para uma lista, com variáveis e delay básico.
   - Blindagem mínima: delay aleatório, limite por instância.

2. **Fase 2 — Respostas e blindagem**
   - Webhook de respostas; vínculo resposta → envio → lead; histórico de conversa; atualização de status do lead.
   - Blindagem completa: lotes, pausas, perfis de conta, aquecimento, rotação, detecção de risco.
   - Spintax e múltiplas variações de mensagem.

3. **Fase 3 — Agendamento e webhook para IA / CRM**
   - Campanhas agendadas e recorrentes; filas por instância.
   - Webhook “resposta” que **aciona a IA** (sistema externo assume a conversa e coloca o lead na esteira); webhook “lead atualizado” para CRM; opção de API de integração (push/pull).
   - Relatórios e exportação (leads, conversas, métricas, leads na esteira).

4. **Fase 4 — Refino e escala**
   - Validação de números (WhatsApp ativo); limpeza de lista.
   - Mapeamento de campos com CRM externo; sync bidirecional (se aplicável).
   - Melhorias de UX, performance e segurança.

---

## 6. Devocional fora do MassFlow

- O **projeto Devocional é outro produto** e fica **completamente excluído** deste escopo.
- O MassFlow **não** inclui envio devocional diário, listas devocionais nem lógica específica de devocional — é **apenas** o disparador voltado a **captação de leads** e **campanhas**.

---

## 7. Resumo executivo

| Pilar | Objetivo |
|-------|----------|
| **Multi-tenant** | Cliente cria conta; listas, leads, campanhas, instâncias e logs próprios; personalização. |
| **Disparos** | Campanhas com variáveis, spintax, multimídia; agendamento e filas; seleção de instâncias. |
| **Blindagem** | Delays aleatórios, lotes, pausas, limites por conta/instância, aquecimento, rotação, detecção de risco. |
| **Respostas / Esteira** | Resposta ligada ao disparo e ao lead; **webhook dispara IA que assume a conversa** (no lugar do número do disparo) e **coloca o lead na esteira**; histórico de conversa; opcional notificar CRM. |
| **Tags / Funis** | Estrutura de tags poderosa; segmentação; tags automáticas pós-disparo; funis efetivos; relatórios por funil. |
| **CRM/Leads** | Banco de leads interno; **manual + CSV + API** (push/pull); integração por webhook/API; mapeamento de campos. |
| **SaaS** | 3 níveis de conta (só minhas / só plataforma / ambas instâncias); créditos avulsos; integração Agentes SaaS. |
| **Boas práticas** | Diversificação de msg, validação de números, opt-in, horário, relatórios, descadastro. |

Com essa visão e ideação, o próximo passo é seguir **MassFlow_ESPECIFICACAO_FINAL.md** e **MassFlow_DOCUMENTO_IMPLANTACAO.md** para implementar o MassFlow em **Projetos-FabriaIA/MassFlow**, integrado ao Agentes SaaS (assinatura e créditos).
