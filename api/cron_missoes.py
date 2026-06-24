import json
import os
import httpx
from http.server import BaseHTTPRequestHandler

from modules.missoes_dia import get_missoes

CHAT_ID = 7137570580


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            missoes = get_missoes()

            if not missoes:
                self._ok("no missions")
                return

            linhas = ["🎯 <b>Missões do dia — como foi?</b>\n"]
            for m in missoes:
                linhas.append(f"• {m['content']}")

            keyboard = []
            for m in missoes:
                nome = m["content"][:28] + ("…" if len(m["content"]) > 28 else "")
                keyboard.append([{"text": f"✅ {nome}", "callback_data": f"m:close:{m['id']}"}])
            if len(missoes) > 1:
                keyboard.append([{"text": "✅ Todas feitas", "callback_data": "m:all"}])

            token = os.getenv("TELEGRAM_BOT_TOKEN")
            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": CHAT_ID,
                    "text": "\n".join(linhas),
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": keyboard},
                },
                timeout=10,
            )
            self._ok("ok")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def _ok(self, msg: str):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": msg}).encode())

    def log_message(self, *args):
        pass
