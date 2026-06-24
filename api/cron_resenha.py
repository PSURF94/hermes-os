import os
from http.server import BaseHTTPRequestHandler

from modules.resenha import gerar_resenha
from notify import notificar


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
