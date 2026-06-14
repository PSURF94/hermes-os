"""
Envia notificação para o Telegram de Paulo.
Uso: python notify.py "mensagem aqui"
Ou importe: from notify import notificar
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAULO_CHAT_ID = "7137570580"


def notificar(mensagem: str) -> bool:
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": PAULO_CHAT_ID, "text": mensagem},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Erro ao notificar: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python notify.py 'mensagem'")
        sys.exit(1)
    msg = " ".join(sys.argv[1:])
    ok = notificar(msg)
    print("Enviado." if ok else "Falhou.")
