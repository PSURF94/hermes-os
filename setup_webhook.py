"""
Rode este script UMA VEZ após o deploy no Vercel para registrar o webhook no Telegram.
Uso: python setup_webhook.py
"""
import urllib.request
import urllib.parse
import json

from config import TELEGRAM_BOT_TOKEN


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Erro: TELEGRAM_BOT_TOKEN não encontrado no .env")
        return

    url = input("URL do Vercel (ex: https://hermes-os.vercel.app): ").strip().rstrip("/")
    webhook_url = f"{url}/api/webhook"

    payload = json.dumps({"url": webhook_url, "drop_pending_updates": True}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    if data.get("ok"):
        print(f"Webhook registrado com sucesso: {webhook_url}")
    else:
        print(f"Erro ao registrar webhook: {data}")


if __name__ == "__main__":
    main()
