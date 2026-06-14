"""
Envia resposta ao Telegram e atualiza status no Supabase.
Lê a resposta do stdin.
Uso: echo "resposta" | python responder_mensagem.py <id>
     python responder_mensagem.py <id> < _resposta.txt
"""
import sys
import os
import httpx
from dotenv import load_dotenv
load_dotenv()

from services.supabase_client import get_client

if len(sys.argv) < 2:
    print("Uso: python responder_mensagem.py <id>")
    sys.exit(1)

mid = sys.argv[1]
resposta = sys.stdin.read().strip()

if not resposta:
    print("Resposta vazia.")
    sys.exit(1)

db = get_client()
r = db.table("mensagens").select("chat_id").eq("id", mid).execute()
if not r.data:
    print(f"Mensagem {mid} não encontrada.")
    sys.exit(1)

chat_id = r.data[0]["chat_id"]

db.table("mensagens").update({
    "resposta": resposta,
    "status": "concluido",
}).eq("id", mid).execute()

token = os.getenv("TELEGRAM_BOT_TOKEN")
resp = httpx.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": resposta},
    timeout=10,
)

if resp.status_code == 200:
    print(f"Enviado para chat {chat_id}.")
else:
    print(f"Erro Telegram {resp.status_code}: {resp.text}")
    sys.exit(1)
