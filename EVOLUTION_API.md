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

## Webhook n8n (resposta do lead + palavras-chave)

1. Na **campanha**: URL do n8n e **palavras-chave** (separadas por vírgula). Só assim o MassFlow filtra e não envia todas as mensagens ao webhook.

2. Na **Evolution API**, webhook da instância com **POST** para:
   - `https://<sua-api>/api/campaigns/inbound/<TENANT_ID>`
   - Evento: mensagens recebidas (`MESSAGES_UPSERT` / `messages.upsert`).

3. Quando o **lead responde** e o texto contém uma palavra-chave, o MassFlow faz `POST` no webhook do n8n com o texto da **resposta do contato**:

| Campo | Descrição |
|-------|-----------|
| `event` | `campaign_reply_keyword_matched` |
| `lead_message` | Texto que o lead digitou (não o texto do disparo) |
| `matched_keywords` | Palavras que casaram |
| `tenant_id`, `campaign_id`, `campaign_name` | Campanha |
| `lead_id`, `lead_name`, `lead_phone` | Lead |
| `source` | `massflow` |

O disparo em massa **não** chama o n8n; apenas o fluxo acima, após resposta filtrada.

Documentação Evolution: https://doc.evolution-api.com/v2/en/configuration/webhooks
