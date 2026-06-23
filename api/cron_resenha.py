import os
from http.server import BaseHTTPRequestHandler

from modules.resenha import gerar_resenha
from notify import notificar


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        secret = os.getenv("CRON_SECRET", "")
        auth = self.headers.get("Authorization", "")
        if secret and auth != f"Bearer {secret}":
            self.send_response(401)
            self.end_headers()
            return

        try:
            resenha = gerar_resenha()
            ok = notificar(resenha, html=True)
            self.send_response(200 if ok else 500)
            self.end_headers()
            self.wfile.write(b"OK" if ok else b"Falhou ao enviar Telegram")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, format, *args):
        pass
