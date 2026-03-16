# MassFlow — Especificação Final (Projeto Preparado para Implantação)

Consolidação de todos os requisitos discutidos: sistema de disparos em massa poderoso e estável, blindagem completa, tags/funis, IA (webhook/API + IA integrada), fontes de contatos (manual, CSV, API), modelo tenant SaaS com 3 níveis de conta e créditos avulsos, e integração com o projeto **Agentes SaaS** (assinatura e créditos). Implantação na pasta raiz **Projetos-FabriaIA** (MassFlow como subprojeto; integração com Agentes SaaS no mesmo ecossistema).

---

## 1. Posicionamento do produto

- **MassFlow** = sistema de **disparos em massa** poderoso, eficiente e estável, **adaptado ao uso da Evolution API**, com todos os **processos e procedimentos de blindagem** para **evitar e mitigar banimentos**.
- Foco em **captação de leads** e **campanhas**, com **estrutura de tags** para **funis efetivos**, **conexão de IAs** (webhook/API) para encaminhar respostas a **agentes de IA**, e **IA integrada** que analisa disparos e sugere próximo passo do funil e tagamento pós-disparo.
- **Multi-tenant SaaS** com assinatura peculiar: 3 níveis de conta (só minhas instâncias / só as da plataforma / ambas) + **créditos avulsos** para disparos; integração com o projeto **Agentes SaaS** para assinatura e créditos.
- **Contatos:** inclusão manual, importação CSV e **consumo via API** (todos os sistemas que utilizarem o MassFlow podem conectar e enviar/receber contatos por API).

---

## 2. Blindagem (evitar e mitigar banimentos)

Manter e reforçar todos os processos e procedimentos já pensados:

- **Delays aleatórios** entre mensagens (nunca fixos); **lotes** com **pausas** entre lotes; **pausa longa** configurável após X mensagens.
- **Limites** por instância e por conta (hora/dia); **perfis de idade** da conta (novo / estabelecido / maduro).
- **Aquecimento** de instâncias novas; **rotação** automática de instâncias; **detecção de risco** (403/429, padrões de falha) e pausa da instância.
- **Conteúdo:** alertas para repetição excessiva; uso de variáveis/spintax; opção de descadastro; **consentimento** e lista limpa (opt-in, desativação de quem pediu saída).

Tudo configurável **por campanha** (e/ou por tenant), para manter o sistema estável e adaptado à Evolution API.

---

## 3. Estrutura de TAGS para funis efetivos

- **Sistema de tags** inteligente e poderoso, no nível do **lead** e da **campanha**, para montar **funis**.
- **Tags no lead:** cada lead pode ter **múltiplas tags** (ex.: `quente`, `interessado`, `comprou`, `funil-vendas-2025`). Tags usadas para **segmentação** em campanhas (enviar só para quem tem tag X ou não tem tag Y).
- **Tags automáticas pós-disparo:** após envio ou após resposta, o sistema (ou a **IA integrada**) pode **sugerir ou aplicar** tags (ex.: “respondeu sim” → tag `qualificado`; “abriu link” → tag `engajado`). Regras manuais (ex.: se respondeu “quero” → tag `na-esteira`) e/ou sugestões da IA.
- **Funil como sequência de etapas:** cada etapa pode ser uma **campanha** ou um **gatilho** (ex.: “recebeu campanha A” → aguardar 2 dias → enviar campanha B só para tag `interessado`). A estrutura de tags permite definir **etapas de funil** (ex.: tags `etapa-1`, `etapa-2`, `concluido`) e relatórios por funil.
- **UI:** gestão de tags (criar, editar, aplicar em massa); filtros por tag em listas e campanhas; histórico de “lead recebeu campanha X → ganhou tag Y” para auditoria do funil.

---

## 4. Conexão de IAs: Webhook/API e Agentes de IA

- **Encaminhamento de respostas para agentes de IA:** quando o lead responde a um disparo, o MassFlow pode:
  - **Webhook:** disparar uma URL configurável (por tenant ou por campanha) com payload (lead_id, campaign_id, texto da resposta, telefone, tags atuais, histórico recente). O sistema externo **aciona a IA** que assume a conversa e coloca o lead na esteira.
  - **API:** o mesmo fluxo pode ser exposto como **evento consumível via API** (polling ou webhook) para sistemas que queiram conectar **agentes de IA** (ex.: Agentes SaaS ou outros) e responder pelo número da IA.
- **Agentes de IA conectados:** o tenant configura uma ou mais “conexões de IA” (URL do webhook ou credenciais de API). Cada resposta qualificada (ou toda resposta) é enviada para esses agentes; o lead sai do fluxo do disparo e entra na **esteira** (status do lead atualizado; opcionalmente nova tag, ex.: `na-esteira`).

---

## 5. IA integrada: análise de disparos e sugestão de próximo passo

- **IA integrada** (dentro do MassFlow ou via serviço interno) que:
  - **Analisa os disparos** (taxa de abertura, resposta, opt-out, tags atuais dos leads).
  - **Sugere o próximo passo do funil:** ex.: “enviar campanha B para quem tem tag `interessado` em 48h” ou “criar campanha de reativação para quem não respondeu em 7 dias”.
  - **Sugere tagamento pós-disparo:** ex.: “aplicar tag `quente` a quem respondeu nas últimas 24h” ou “tag `frio` para quem não abriu as últimas 3 campanhas”.
- Implementação pode ser: **regras configuráveis** (sem IA) no primeiro momento; depois **chamada a um modelo** (API interna ou Agentes SaaS) que recebe contexto (campanha, métricas, lista de leads) e retorna sugestões (próxima campanha, tags sugeridas). A interface exibe “Sugestões da IA” e permite aplicar com um clique (ou agendar).

---

## 6. Instâncias (manter como está)

- **Forma de conectar instâncias** permanece como já desenhado:
  - Cada tenant pode ter **suas próprias instâncias** (Evolution API do cliente) e/ou usar **instâncias da plataforma** (conforme nível da conta — ver seção 8).
  - Cadastro por instância: name, api_url, api_key, display_name, limites, health check, rotação (round_robin, least_used, por tag/lead).
- Nenhuma mudança estrutural; apenas a **origem** das instâncias (próprias vs plataforma vs ambas) é controlada pelo **nível da conta** e pela **assinatura**.

---

## 7. Fontes de contatos: manual, CSV e API

Ordem de implementação e uso:

1. **Inclusão manual:** cadastro de contatos um a um (telefone, nome, email, campos custom, tags). Essencial para o primeiro uso.
2. **Importação CSV:** upload de arquivo (CSV/Excel) com mapeamento de colunas (telefone obrigatório; nome, email, tags e campos custom opcionais). Importação para uma **lista** existente ou criação de lista na hora. Validação básica (duplicados, formato de telefone).
3. **Consumo via API (conexão de sistemas):** todos os sistemas que forem utilizar o MassFlow poderão **enviar e receber contatos** via API.

**Sugestão de estrutura para API de contatos:**

- **Enviar contatos para o MassFlow (push):**
  - `POST /api/contacts/sync` ou `POST /api/contacts/import`
  - Body: lista de contatos com `phone` (obrigatório), `name`, `email`, `tags[]`, `custom_fields{}`, `list_id` ou `list_slug`.
  - Opção: `upsert` por telefone (atualizar se já existir no tenant). Resposta: total criados, atualizados, erros.
- **Receber contatos do MassFlow (pull):**
  - `GET /api/contacts` com filtros: `list_id`, `tags[]`, `updated_since` (ISO datetime), paginação.
  - Resposta: array de leads com telefone, nome, email, tags, custom_fields, last_sent_at, last_response_at, status (ativo, na_esteira, opt_out).
- **Webhook de alteração (opcional):** quando um lead for atualizado (nova tag, resposta, entrada na esteira), chamar URL do cliente (webhook) com payload do lead — para sistemas que preferirem não fazer polling.

Com isso, cada sistema (CRM, site, Agentes SaaS, etc.) pode **incluir manualmente**, **importar CSV** e **sincronizar por API** com o MassFlow.

---

## 8. Modelo tenant SaaS: 3 níveis de conta + créditos avulsos

Modelo de assinatura **peculiar** com três níveis básicos de conta, mais a opção de **comprar créditos avulsos** para disparos.

### 8.1 Três níveis de conta

| Nível | Nome (sugestão) | Instâncias | Uso típico |
|-------|------------------|------------|------------|
| **1** | **Só minhas** (Bring Your Own) | Cliente **conecta apenas as próprias instâncias** (Evolution API dele). Plataforma não fornece número. | Quem já tem números e Evolution própria. |
| **2** | **Só da plataforma** | Cliente usa **apenas instâncias da plataforma** (números gerenciados por você). Sem conectar instância própria. | Quem quer começar sem configurar Evolution. |
| **3** | **Híbrido** | Cliente pode ter **suas instâncias e as da plataforma** **na mesma conta**. Rotação e campanhas podem usar ambos os conjuntos. | Máxima flexibilidade. |

- No cadastro/assinatura o tenant recebe um **plano** (nível 1, 2 ou 3). O backend **valida** ao criar/editar instância: nível 1 → só instâncias com `owner = tenant`; nível 2 → só instâncias com `owner = platform`; nível 3 → ambos.
- Limites de **volume de disparos** (mensagens/mês ou/dia) podem vir do **Agentes SaaS** (assinatura) e/ou do próprio MassFlow (config por plano).

### 8.2 Créditos avulsos

- Além da assinatura (que pode incluir um pacote de mensagens), o cliente pode **comprar créditos avulsos** para disparos (ex.: pacote de 1.000 ou 5.000 mensagens).
- **Créditos** são consumidos a cada mensagem enviada (1 envio = 1 crédito, ou regra configurável). Saldo de créditos por tenant armazenado no MassFlow e/ou no **Agentes SaaS** (se a cobrança e o saldo ficarem centralizados lá).
- Ao rodar uma campanha: verificar **assinatura ativa** e **saldo (créditos incluídos)**; debitar após cada envio (ou em lote ao final da campanha). Se não houver saldo, bloquear envio e exibir mensagem para comprar créditos ou renovar plano.

---

## 9. Integração com o projeto Agentes SaaS

- No ecossistema **Projetos-FabriaIA**, existe o projeto **Agentes SaaS**, que já possui **assinatura** e **créditos**.
- **MassFlow** deve **integrar-se** a esse projeto para:
  - **Assinatura:** plano do tenant (nível 1, 2 ou 3) e status (ativo, suspenso, cancelado) podem ser consultados via API ou banco compartilhado do Agentes SaaS. Se o Agentes SaaS for a “fonte da verdade” de billing, o MassFlow apenas **consulta** e **respeita** o plano e o status.
  - **Créditos:** compra e saldo de **créditos avulsos** podem ser gerenciados no Agentes SaaS; o MassFlow **consome** créditos ao disparar (chamada à API do Agentes SaaS para debitar ou leitura de saldo em tempo real). Alternativa: MassFlow mantém uma **cópia** do saldo (sincronizada via webhook/evento do Agentes SaaS) para não depender de latência da API em todo envio.
- **Onde fica o código:** implantação na **pasta raiz Projetos-FabriaIA**; **MassFlow** em `Projetos-FabriaIA/MassFlow/` (backend, frontend, docs). O **Agentes SaaS** pode estar em outra pasta no mesmo repositório ou em repo separado; a integração é por **API** ou **eventos** (e, se aplicável, banco compartilhado apenas para leitura de plano/créditos).
- Documento de implantação e visão passam a referenciar: “Integração com Agentes SaaS para assinatura e créditos” e “MassFlow implantado em Projetos-FabriaIA/MassFlow”.

---

## 10. Resumo: o que o sistema entrega (final)

| Área | Entregável |
|------|------------|
| **Disparos** | Campanhas (único, agendado, recorrente); variáveis, spintax, multimídia; seleção de instâncias; filas e agendamento. |
| **Blindagem** | Delays aleatórios, lotes, pausas, limites, aquecimento, rotação, detecção de risco; configurável por campanha; estável para Evolution API. |
| **Tags e funis** | Tags em leads; segmentação por tag; tags automáticas pós-disparo; funis como sequência de etapas/campanhas; relatórios por funil. |
| **IA externa** | Webhook/API para encaminhar respostas a **agentes de IA**; lead sai do disparo e entra na esteira; status e tags atualizáveis. |
| **IA integrada** | Análise de disparos; sugestão de **próximo passo do funil** e de **tagamento pós-disparo**; exibição e aplicação na interface. |
| **Instâncias** | Manter forma atual; origem controlada pelo nível da conta (só minhas / só plataforma / ambas). |
| **Contatos** | Manual, importação CSV e **API** (push/sync e pull; estrutura sugerida para sistemas externos). |
| **Tenant SaaS** | **3 níveis:** (1) só minhas instâncias, (2) só da plataforma, (3) ambas na mesma conta. **Créditos avulsos** para disparos; integração com **Agentes SaaS** (assinatura + créditos). |
| **Local** | Projetos-FabriaIA; MassFlow em `MassFlow/`; integração com Agentes SaaS no mesmo ecossistema. |

Com essa especificação, o projeto fica **preparado para implantação** na pasta raiz Projetos-FabriaIA, com MassFlow como subprojeto e integração clara ao Agentes SaaS para assinatura e créditos.
