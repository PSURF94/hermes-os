"""
Lê a próxima mensagem pendente do Supabase e marca como "processando".
Output: JSON com {id, conteudo, chat_id} ou "NENHUMA"
Uso: python peek_mensagem.py
"""
import json
import sys
from dotenv import load_dotenv
load_dotenv()

from services.supabase_client import get_client

db = get_client()
r = (
    db.table("mensagens")
    .select("id, conteudo, chat_id, imagem_url")
    .eq("status", "pendente")
    .order("criado_em")
    .limit(1)
    .execute()
)

if not r.data:
    print("NENHUMA")
    sys.exit(0)

msg = r.data[0]
db.table("mensagens").update({"status": "processando"}).eq("id", msg["id"]).execute()
print(json.dumps(msg, ensure_ascii=False))
