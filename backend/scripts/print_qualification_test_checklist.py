#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Imprime ordem e exemplos de chamadas para testar qualificacao + reconciliacao SaaS."""


def main() -> None:
    print(
        r"""
================================================================================
MassFlow - teste minimo (copie BASE e segredos do seu .env / Easypanel)
================================================================================

Variaveis de ambiente no BACKEND (obrigatorias para o fluxo):
  QUALIFICATION_SECRET
  RECEPTION_CONTEXT_SECRET
  SAAS_CHAT_HISTORY_DATABASE_URL   (reconciliacao a partir do Postgres SaaS)
  RECONCILE_SAAS_RETRY_DELAYS_SECONDS=30,60,120   (opcional)

Ordem sugerida:

1) Lead responde a campanha; Evolution chama POST /api/campaigns/inbound/{tenant_id}
   Isso cria linha em campaign_inbound_replies com o campaign_id CORRETO (ultimo disparo).

2) n8n grava contexto de recepcao:
   POST /api/reception-context
   Header: X-Massflow-Reception-Secret: <RECEPTION_CONTEXT_SECRET>
   Body JSON: tenant_id, lead_phone, msg_recepcao, (opcionais lead_id, campaign_id, ...)

3) Agente busca contexto e dispara reconciliacao em background:
   GET /api/reception-context/next-first-interaction?tenant_id=T&lead_phone=P
   Header: mesmo segredo de recepcao.
   Resposta inclui: campaign_id_resolved, reconcile_saas_scheduled (se SaaS + config ok).

4) Estado da qualificacao SEM passar campaign_id (usa ultimo inbound):
   GET /api/qualification/session-state?tenant_id=T&lead_phone=P
   Header: X-Massflow-Qualification-Secret: <QUALIFICATION_SECRET>
   Resposta: campaign_id = campanha resolvida; use esse id no POST /answer.

5) Registrar respostas:
   POST /api/qualification/answer
   Header: X-Massflow-Qualification-Secret
   JSON: tenant_id, campaign_id (o da etapa 4), lead_phone, step_key, answer
   Cada chamada incompleta dispara reconciliacao SaaS em background (after_answer).

6) Manual (opcional):
   POST /api/qualification/reconcile-from-saas?tenant_id=T&campaign_id=C&lead_phone=P

7) Conferir GET /api/campaigns/inbound-replies (JWT) - campo agent_context_consumed apos passo 3.

================================================================================
Exemplo curl (substitua HOST, T, P, segredos):
================================================================================

curl -sS "HOST/api/qualification/session-state?tenant_id=T&lead_phone=P" \
  -H "X-Massflow-Qualification-Secret: QUALIFICATION_SECRET"

curl -sS -X POST "HOST/api/qualification/answer" \
  -H "Content-Type: application/json" \
  -H "X-Massflow-Qualification-Secret: QUALIFICATION_SECRET" \
  -d "{\"tenant_id\":T,\"campaign_id\":C,\"lead_phone\":\"P\",\"step_key\":\"A\",\"answer\":\"cartao\"}"

"""
    )


if __name__ == "__main__":
    main()
