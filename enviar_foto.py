"""
Envia uma foto para o Telegram de Paulo.
Uso: python enviar_foto.py <caminho_arquivo> [legenda opcional]
"""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAULO_CHAT_ID = "7137570580"


def enviar_foto(caminho: str, legenda: str = "") -> bool:
    try:
        with open(caminho, "rb") as f:
            resp = httpx.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto",
                data={"chat_id": PAULO_CHAT_ID, "caption": legenda},
                files={"photo": ("foto.png", f, "image/png")},
                timeout=30,
            )
        return resp.status_code == 200
    except Exception as e:
        print(f"Erro ao enviar foto: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python enviar_foto.py <caminho> [legenda]")
        sys.exit(1)
    caminho = sys.argv[1]
    legenda = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    ok = enviar_foto(caminho, legenda)
    print("Enviado." if ok else "Falhou.")
