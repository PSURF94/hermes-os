"""
Ponte entre Claude e Hermes OS.
Claude escreve _sync.json com o estado atual dos projetos e chama este script.
O script upserta tudo no Supabase para o bot Hermes consultar.

Uso: python sync_hermes.py  (lê _sync.json automaticamente)
"""
import json
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from services.supabase_client import get_client

SYNC_FILE = Path(__file__).parent / "_sync.json"


def sync(projetos: list):
    db = get_client()
    hoje = date.today().isoformat()

    for p in projetos:
        db.table("projetos").upsert({
            "nome": p["nome"],
            "objetivo": p.get("objetivo", ""),
            "status": p.get("status", "ativo"),
            "proxima_acao": p.get("proxima_acao", ""),
            "ultima_atualizacao": hoje,
        }, on_conflict="nome").execute()

        if p.get("contexto"):
            db.table("contexto_projetos").delete().eq("projeto_nome", p["nome"]).execute()
            for item in p["contexto"]:
                db.table("contexto_projetos").insert({
                    "projeto_nome": p["nome"],
                    "tipo": item["tipo"],
                    "conteudo": item["conteudo"],
                }).execute()

        print(f"  OK  {p['nome']}")


def main():
    if not SYNC_FILE.exists():
        print(f"Arquivo _sync.json não encontrado em {SYNC_FILE.parent}")
        sys.exit(1)

    data = json.loads(SYNC_FILE.read_text(encoding="utf-8"))
    print(f"\nSincronizando {len(data)} projeto(s) com Hermes...\n")
    sync(data)
    SYNC_FILE.unlink()
    print("\nSync concluído.")


if __name__ == "__main__":
    main()
