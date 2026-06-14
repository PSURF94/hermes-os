"""
Marca tarefa como concluída e salva a resposta.
Uso: python concluir_tarefa.py <id> "resposta aqui"
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

from services.supabase_client import get_client

if len(sys.argv) < 3:
    print("Uso: python concluir_tarefa.py <id> 'resposta'")
    sys.exit(1)

task_id = int(sys.argv[1])
resposta = " ".join(sys.argv[2:])

db = get_client()
db.table("mensagens").update({"status": "concluido", "resposta": resposta}).eq("id", task_id).execute()
print(f"Tarefa {task_id} concluída.")
