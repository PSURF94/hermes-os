import os
import httpx
from http.server import BaseHTTPRequestHandler

from modules.resenha import gerar_resenha
from modules.missoes_dia import set_pendente, build_keyboard_raw
from services.todoist import listar_tarefas, listar_projetos_todoist
from modules.briefing import PROJETOS_OCULTOS_BRIEFING
from services.estado import set_config
from notify import notificar

CHAT_ID = 7137570580


def _tarefas_para_selecao() -> list:
    try:
        projetos = listar_projetos_todoist()
        ids_excluidos = {p["id"] for p in projetos if p.get("name") in PROJETOS_OCULTOS_BRIEFING}
    except Exception:
        ids_excluidos = set()
    tarefas = listar_tarefas()
    filtradas = [t for t in tarefas if t.get("project_id") not in ids_excluidos]
    return [{"id": t["id"], "content": t["content"]} for t in filtradas[:8]]


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
            notificar(resenha, html=True)

            # Prepara seleção de missões do dia
            tarefas = _tarefas_para_selecao()
            set_pendente(tarefas)
            set_config("ms_selecionadas", [])

            keyboard = build_keyboard_raw(tarefas, [])
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": CHAT_ID,
                    "text": "🎯 <b>Quais são suas missões de hoje?</b>\n\nSelecione nas tarefas abaixo ou adicione uma nova:",
                    "parse_mode": "HTML",
                    "reply_markup": {"inline_keyboard": keyboard},
                },
                timeout=10,
            )

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, format, *args):
        pass
