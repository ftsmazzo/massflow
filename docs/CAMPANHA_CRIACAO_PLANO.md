# Criação de Campanha — Plano

Documento que define como será a **criação de campanhas** no MassFlow: vínculos (blindagem, lista, instâncias), conteúdo (mídia e variáveis de texto) e fluxo de criação.

---

## 1. Visão geral

Uma **campanha** é uma ação de disparo em massa que envolve:

| Elemento | Descrição |
|----------|-----------|
| **Público** | Uma **lista** (contatos que já estão na lista; lista é construída em Listas com Import CSV ou seleção de contatos). |
| **Blindagem** | Configuração de proteção anti-ban: delays, lotes, pausas, limites, horário. Pode usar a **config global** do tenant (Blindagem) ou permitir **ajuste por campanha** (override). |
| **Instâncias** | Quais instâncias WhatsApp (Evolution) usar; rotação conforme blindagem. |
| **Conteúdo** | O que enviar: **texto** (com variáveis e spintax), **imagem**, **vídeo**, **áudio**, ou **combinações** (ex.: imagem + texto, vídeo + texto, áudio + texto). |
| **Agendamento** | Imediato ou agendado (data/hora). |

A página **Contatos** não é fonte de inclusão de contatos: serve só para **visualização, filtros, manipulação** (editar, excluir, tags) e **informações de volume/dados**. A inclusão de contatos acontece em **Listas** (Importar CSV ou adicionar contatos existentes).

---

## 2. Conteúdo da campanha: mídia e texto

### 2.1 Tipos de mídia (Evolution API)

- **Texto** — mensagem de texto.
- **Imagem** — arquivo de imagem (jpeg, png, etc.) + legenda opcional.
- **Vídeo** — arquivo de vídeo + legenda opcional.
- **Áudio** — arquivo de áudio (ex.: áudio do WhatsApp).
- **Documento** — PDF, etc., com legenda opcional.

### 2.2 Combinações suportadas

- **Texto sozinho**
- **Imagem + texto** (legenda)
- **Vídeo + texto** (legenda)
- **Áudio + texto** (mensagem antes/depois)
- **Documento + texto** (legenda)

Ou seja: sempre pode haver um **texto** (variável) acompanhando qualquer mídia. O backend/Evolution envia na ordem adequada (ex.: texto + mídia ou mídia com caption).

### 2.3 Variáveis no texto

- **Variáveis do lead:** `{nome}`, `{telefone}`, `{email}` e campos custom (ex.: `{empresa}`). Substituídas no envio por contato.
- **Spintax (variação):** sintaxe para variar trechos, ex.: `{Olá|Oi|Bom dia}, {nome}!` — uma opção escolhida por envio (aleatória ou determinística por lead_id para consistência).

Recomendação de produto: alertar se o texto não tiver pelo menos uma variável (ex.: nome), para incentivar personalização (alinhado à blindagem de conteúdo).

### 2.4 Armazenamento de mídia

- Arquivos (imagem, vídeo, áudio) precisam ser **enviados** (upload) e referenciados na campanha (URL ou ID interno).
- Opções: upload para storage (S3, local) e URL; ou base64 no banco (menos recomendado para arquivos grandes). Evolution API aceita URL ou base64.
- Definir tamanho máximo e formatos aceitos por tipo.

---

## 3. Vínculos na criação da campanha

### 3.1 Lista (público-alvo)

- Campanha escolhe **uma lista**.
- Os contatos que receberão a campanha são os da lista no momento do disparo (ou no agendamento).
- Filtro opcional por **tags** (ex.: enviar só para quem tem tag X ou não tem Y) aplicado sobre os contatos da lista.

### 3.2 Blindagem

- **Config global** (já existe): tela Blindagem por tenant (delays, lotes, limites, horário, etc.).
- **Campanha** pode:
  - **Usar só a global** (recomendado), ou
  - **Sobrescrever** parte dos parâmetros (ex.: delay maior para esta campanha).
- Na tela de criação: seleção “Usar configuração global” ou “Personalizar para esta campanha” (form com os mesmos campos, opcionais).

### 3.3 Instâncias

- Campanha escolhe **quais instâncias** usar (ou “todas disponíveis”).
- A blindagem (rotação, limites por instância) define como distribuir a fila entre elas.

---

## 4. Fluxo de criação (passos sugeridos)

1. **Nome e tipo** — Nome da campanha; tipo: disparo único ou agendado.
2. **Público** — Escolher **lista**; opcional: filtro por tags.
3. **Conteúdo** — Escolher tipo de mídia (texto, imagem, vídeo, áudio, documento) e combinações; escrever texto com variáveis/spintax; fazer upload de mídia se necessário.
4. **Blindagem** — Usar global ou personalizar para esta campanha.
5. **Instâncias** — Selecionar instâncias (ou todas).
6. **Revisão e envio** — Preview, total de contatos, estimativa de tempo; botão “Agendar” ou “Disparar agora”.

---

## 5. Modelo de dados (campanha)

- **Campaign:** tenant_id, name, type (immediate | scheduled), list_id, tag_filter (opcional), content (JSON: type, text, media_urls, etc.), shielding_config (JSON, opcional override), instance_ids (ou “all”), status, scheduled_at, created_at, updated_at.
- **Tabela de envios:** campaign_id, lead_id, sent_at, message_id (Evolution), status (pending, sent, delivered, failed), etc.

---

## 6. Resumo

| Tema | Decisão |
|------|---------|
| **Contatos** | Página Contatos = só visualização, filtro, manipulação e volumes; **não** inclui “Novo contato” nem “Importar CSV”. |
| **Inclusão de contatos** | Em **Listas**: Importar CSV para uma lista ou adicionar contatos existentes à lista. |
| **Campanha** | Lista + blindagem + instâncias + conteúdo (mídia + texto com variáveis/spintax) + agendamento. |
| **Mídia** | Texto, imagem, vídeo, áudio, documento; combinações com texto (legenda ou mensagem). |
| **Texto** | Variáveis `{nome}`, etc.; spintax para variação. |
| **Blindagem** | Global por tenant; campanha pode usar global ou sobrescrever. |

Com isso, a criação de campanha fica clara e alinhada a blindagem, contatos (via lista) e mídia variada.
