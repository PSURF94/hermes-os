"""
Busca a próxima tarefa pendente em mensagens e marca como em_processamento.
Retorna o conteúdo da tarefa (ou vazio se não houver).

Uso: python pegar_tarefa.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

from services.supabase_client import get_client

db = get_client()

r = (
    db.table("mensagens")
    .select("id, conteudo")
    .eq("status", "pendente")
    .order("criado_em")
    .limit(1)
    .execute()
)

if not r.data:
    print("")
    sys.exit(0)

row = r.data[0]
db.table("mensagens").update({"status": "em_processamento"}).eq("id", row["id"]).execute()

print(f"ID:{row['id']}|{row['conteudo']}")
