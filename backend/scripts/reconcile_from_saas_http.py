#!/usr/bin/env python3
"""
Chama POST /api/qualification/reconcile-from-saas no deploy (ou local) sem remontar campanha no front.

Variáveis de ambiente:
  MASSFLOW_API        URL base (ex.: https://seu-dominio.com ou vazio para http://127.0.0.1:8000)
  QUALIFICATION_SECRET  Mesmo valor de QUALIFICATION_SECRET do backend (header ou Bearer)

Exemplo (PowerShell):
  $env:MASSFLOW_API="https://api.exemplo.com"
  $env:QUALIFICATION_SECRET="seu-segredo"
  python backend/scripts/reconcile_from_saas_http.py --tenant-id 1 --campaign-id 2 --phone 5516999999999

Com pré-visualização do resumo sem enviar WhatsApp:
  python ... --no-whatsapp
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="Reconciliar qualificação a partir do SaaS (chatMessages).")
    p.add_argument("--tenant-id", type=int, required=True)
    p.add_argument("--campaign-id", type=int, required=True)
    p.add_argument("--phone", required=True, help="Lead phone (dígitos, ex.: 5516999999999)")
    p.add_argument("--lead-id", type=int, default=None)
    p.add_argument("--lead-name", default=None)
    p.add_argument(
        "--no-whatsapp",
        action="store_true",
        help="send_whatsapp=false: só grava e mostra classification_summary_text",
    )
    args = p.parse_args()

    base = (os.environ.get("MASSFLOW_API") or "http://127.0.0.1:8000").rstrip("/")
    secret = (os.environ.get("QUALIFICATION_SECRET") or "").strip()
    if not secret:
        print("Defina QUALIFICATION_SECRET no ambiente.", file=sys.stderr)
        return 1

    q = {
        "tenant_id": args.tenant_id,
        "campaign_id": args.campaign_id,
        "lead_phone": args.phone,
        "send_whatsapp": "false" if args.no_whatsapp else "true",
    }
    if args.lead_id is not None:
        q["lead_id"] = str(args.lead_id)
    if args.lead_name:
        q["lead_name"] = args.lead_name

    url = f"{base}/api/qualification/reconcile-from-saas?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "X-Massflow-Qualification-Secret": secret,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(f"HTTP {e.code}: {err_body or e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(str(e.reason), file=sys.stderr)
        return 1

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return 0

    print(json.dumps(data, ensure_ascii=False, indent=2))
    summary = data.get("classification_summary_text")
    if summary:
        print("\n--- classification_summary_text (resumo / msg classificatória) ---\n")
        print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
