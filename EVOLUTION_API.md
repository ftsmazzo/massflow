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

## Webhook de mensagens recebidas (resposta do lead → IA)

O disparo de campanha **não** envia automaticamente as respostas do WhatsApp para o seu n8n/Chatwoot. Para o MassFlow qualificar a resposta (palavras-chave) e **encaminhar** nome, telefone e mensagem ao webhook do agente:

1. Na **Evolution API**, configure o webhook da instância com:
   - **URL:** `https://<sua-api-massflow>/api/campaigns/inbound/<TENANT_ID>`
   - **Evento:** `MESSAGES_UPSERT` (ou equivalente `messages.upsert` na sua versão)
   - Método **POST** com JSON (como a Evolution envia por padrão)

2. No **formulário da campanha** no MassFlow:
   - **Webhook para resposta com interesse** = URL do **agente** (n8n), ex.: `https://.../webhook/tenant_x/agent_y`
   - **Palavras-chave** = termos que indicam interesse

Fluxo: **Evolution → MassFlow** (`/api/campaigns/inbound/...`) → se bater palavra-chave → **POST** para o webhook do agente.

**Importante:** a URL que você coloca na Evolution **não** é a do n8n; é a do backend MassFlow acima. O n8n só recebe o encaminhamento depois que o MassFlow processar.

**Diagnóstico:** chame o endpoint com `?debug=1` em ambiente de teste; a resposta JSON inclui dicas se o telefone ou o formato do payload não bateram.

Documentação Evolution sobre webhooks: https://doc.evolution-api.com/v2/en/configuration/webhooks
