import json
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update

from handlers import setup_application


async def _process(update_data: dict) -> None:
    app = setup_application()
    async with app:
        update = Update.de_json(update_data, app.bot)
        await app.process_update(update)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            asyncio.run(_process(json.loads(body)))
        except Exception as e:
            print(f"Erro ao processar update: {e}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass
