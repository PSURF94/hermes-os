import os
import httpx
from datetime import date
from http.server import BaseHTTPRequestHandler

from modules.missoes_dia import set_pendente, build_keyboard_raw
from services.todoist import listar_tarefas, listar_projetos_todoist
from modules.briefing import PROJETOS_OCULTOS_BRIEFING
from services.estado import set_config

CHAT_ID = 7137570580
MAX_SELECAO = 20


def _due_info(tarefa: dict) -> tuple[int, str, str]:
    """Retorna (prioridade_sort, due_str_display, data_iso) para ordenação e exibição."""
    due = tarefa.get("due") or {}
    data_str = due.get("date", "")
    if not data_str:
        return (3, "", "")
    try:
        d = date.fromisoformat(data_str[:10])
        hoje = date.today()
        if d < hoje:
            delta = (hoje - d).days
            return (0, f"[{delta}d atrás]", data_str)
        elif d == hoje:
            return (1, "[hoje]", data_str)
        else:
            return (2, f"[{d.strftime('%d/%m')}]", data_str)
    except Exception:
        return (3, "", "")


def _tarefas_para_selecao() -> list:
    try:
        projetos = listar_projetos_todoist()
        ids_excluidos = {p["id"] for p in projetos if p.get("name") in PROJETOS_OCULTOS_BRIEFING}
    except Exception:
        ids_excluidos = set()

    tarefas = listar_tarefas()
    filtradas = [t for t in tarefas if t.get("project_id") not in ids_excluidos]

    # separa com e sem data de vencimento
    com_data = [t for t in filtradas if t.get("due")]
    sem_data = [t for t in filtradas if not t.get("due")]

    # com data: atrasadas → hoje → futuras
    com_data.sort(key=lambda t: _due_info(t)[2])

    # sem data: mais recentes primeiro (created_at DESC)
    sem_data.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    ordenadas = com_data + sem_data

    resultado = []
    for t in ordenadas[:MAX_SELECAO]:
        _, due_str, _ = _due_info(t)
        resultado.append({
            "id":      t["id"],
            "content": t["content"],
            "due_str": due_str,
        })
    return resultado


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
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

    def log_message(self, *args):
        pass
