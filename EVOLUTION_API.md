# Integração Evolution API

O MassFlow integra com **Evolution API** para envio de mensagens WhatsApp (instâncias, QR, texto e mídia).

## Versão mínima

- **Evolution API: 2.3.7** (ou superior).  
  Alterações que afetam envio de mídia devem consultar a documentação desta versão.

## Documentação oficial

- **Índice geral:** https://doc.evolution-api.com/llms.txt  
- **Send Media (sendMedia):** https://doc.evolution-api.com/v2/api-reference/message-controller/send-media  
- **Send Text (sendText):** usado para mensagens só texto.  
- **Instance (create, connect, connectionState, logout):** criação e conexão de instâncias.

## Send Media (POST /message/sendMedia/{instance})

Corpo esperado (JSON):

| Campo      | Obrigatório | Descrição                                      |
|-----------|-------------|------------------------------------------------|
| number    | sim         | Número com DDI (apenas dígitos)                |
| mediatype | sim         | `Image`, `Video`, `Audio` ou `Document`        |
| mimetype  | sim         | Ex.: `image/png`, `image/jpeg`                  |
| caption   | sim         | Legenda (pode ser string vazia)                |
| media     | sim         | URL **ou** string em **base64 puro** (sem prefixo `data:...`) |
| fileName  | sim         | Nome do arquivo com extensão (ex.: `foto.jpg`)  |

Header: `apikey` com a chave da API.

## Tamanho de mídia

- **Upload (MassFlow):** até 50 MB (nginx e backend configurados).
- **WhatsApp / Evolution:** para melhor entrega, imagens menores (ex.: &lt; 5 MB) costumam funcionar melhor. Se o envio falhar, verifique a mensagem de erro em `campaign_messages.error_message` (a resposta da Evolution API é gravada ali).

## Referência no código

- `backend/app/services/evolution.py` — chamadas à Evolution API; comentário no topo do arquivo indica versão e links da doc.

## Webhook n8n (URL na campanha)

Na **campanha**, campo **Webhook n8n** (opcional). Com URL preenchida:

### A) Cada envio da campanha

Após cada mensagem **enviada com sucesso** a um lead, o MassFlow faz `POST` no mesmo webhook:

| Campo | Descrição |
|-------|-----------|
| `event` | `campaign_message_sent` |
| `message_text` | Texto (ou legenda) enviado ao lead |
| `content_type` | `text`, `image`, etc. |
| `tenant_id`, `campaign_id`, `campaign_name` | Campanha |
| `lead_id`, `lead_name`, `lead_phone` | Lead |
| `source` | `massflow` |

### B) Respostas do lead (Evolution → MassFlow)

1. Na **Evolution API**, webhook da instância com **POST** para:
   - `https://<sua-api>/api/campaigns/inbound/<TENANT_ID>`
   - Evento: `messages.upsert`.

2. Para **cada resposta** recebida (após um disparo da campanha para aquele lead), o MassFlow faz `POST` no webhook do n8n:

| Campo | Descrição |
|-------|-----------|
| `event` | `campaign_reply_received` |
| `lead_message` | Texto que o lead digitou |
| `matched_keywords` | Palavras da campanha que aparecem no texto (opcional; vazio se você não configurou keywords) |
| `tenant_id`, `campaign_id`, `campaign_name` | Campanha |
| `lead_id`, `lead_name`, `lead_phone` | Lead |
| `source` | `massflow` |

Filtro por palavra-chave no n8n: use `matched_keywords` ou o texto em `lead_message`. O MassFlow **não bloqueia** envio por keyword.

### URL exata do webhook

- Com login no MassFlow, chame **`GET /api/campaigns/inbound-config`** (no mesmo host em que a API roda). A resposta traz `inbound_webhook_url` montada a partir do pedido (scheme + host + path). Atrás de proxy reverso, configure repasse de host/proto (ex.: uvicorn com `--proxy-headers`) para a URL sair com `https` correto.

### Se o n8n não receber nada

1. **URL do webhook** preenchida na campanha (a mesma para envio + respostas).
2. **Respostas:** webhook da **Evolution** apontando para `POST .../api/campaigns/inbound/<TENANT_ID>` (`messages.upsert`). Sem isso não há `campaign_reply_received`.
3. **`?debug=true`** no inbound quando não extrai texto/telefone (`sem_texto_ou_telefone`).
4. **Motivos** na resposta JSON do inbound: `lead_nao_encontrado`, `sem_disparo_previo` (lead sem envio de campanha antes), `webhook_nao_configurado`, `erro_ao_enviar_webhook`.

Documentação Evolution: https://doc.evolution-api.com/v2/en/configuration/webhooks
