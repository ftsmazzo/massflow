"""
Importa instâncias Evolution a partir de um CSV para a tabela evolution_instances.

Uso (na pasta backend, com .env configurado):
  python -m app.scripts.import_instances_csv instancias.csv --tenant-id 1

Ou com tenant pelo slug:
  python -m app.scripts.import_instances_csv instancias.csv --tenant-slug meu-tenant

Formato do CSV (com cabeçalho):
  - name          : nome de exibição (ex: "MotriG - 05") -> display_name
  - instance_name : nome na Evolution API (ex: "assistente-05") -> name
  - api_url       : URL base da Evolution (ex: https://motrig-evolution-api.easypanel.host)
  - api_key       : chave da API
  - status        : opcional (ex: connected); default "connected"

Se o CSV tiver só "name" e não tiver "instance_name", name será usado nos dois (name e display_name).
"""
from __future__ import annotations

import argparse
import csv
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa instâncias Evolution de um CSV")
    parser.add_argument("csv_path", help="Caminho do arquivo CSV")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--tenant-id", type=int, help="ID do tenant que receberá as instâncias")
    g.add_argument("--tenant-slug", type=str, help="Slug do tenant (ex: meu-tenant)")
    parser.add_argument("--owner", default="tenant", choices=("tenant", "platform"), help="owner das instâncias")
    args = parser.parse_args()

    # Importações que dependem do app (env, DB)
    from app.database import SessionLocal
    from app.models.evolution_instance import EvolutionInstance
    from app.models.tenant import Tenant

    path = os.path.abspath(args.csv_path)
    if not os.path.isfile(path):
        print(f"Arquivo não encontrado: {path}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        if args.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == args.tenant_id).first()
        else:
            tenant = db.query(Tenant).filter(Tenant.slug == args.tenant_slug).first()
        if not tenant:
            print("Tenant não encontrado.", file=sys.stderr)
            sys.exit(1)

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print("CSV vazio ou sem cabeçalho.", file=sys.stderr)
                sys.exit(1)
            # Normalizar chaves: minúsculo, sem espaços extras
            def norm(s: str) -> str:
                return s.strip().lower().replace(" ", "_") if s else ""

            rows = []
            for row in reader:
                rows.append({norm(k): (v.strip() if isinstance(v, str) else v) for k, v in row.items()})

        created = 0
        skipped = 0
        for r in rows:
            # Mapear colunas possíveis do CSV (outro banco / planilha)
            name_evolution = (r.get("instance_name") or r.get("name") or "").strip()
            display = (r.get("name") or r.get("display_name") or name_evolution or "").strip()
            api_url = (r.get("api_url") or "").strip()
            api_key = (r.get("api_key") or "").strip()
            status = (r.get("status") or "connected").strip() or "connected"

            if not name_evolution or not api_url:
                skipped += 1
                continue

            existing = db.query(EvolutionInstance).filter(
                EvolutionInstance.tenant_id == tenant.id,
                EvolutionInstance.name == name_evolution,
                EvolutionInstance.owner == args.owner,
            ).first()
            if existing:
                skipped += 1
                continue

            inst = EvolutionInstance(
                tenant_id=tenant.id,
                name=name_evolution,
                api_url=api_url,
                api_key=api_key,
                display_name=display or name_evolution,
                owner=args.owner,
                status=status,
                limits={},
            )
            db.add(inst)
            created += 1

        db.commit()
        print(f"Importadas: {created}. Ignoradas/duplicadas: {skipped}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
