from datetime import datetime
from zoneinfo import ZoneInfo

from services.google_calendar import (
    listar_eventos_hoje,
    listar_eventos_semana,
    criar_evento,
    deletar_evento_por_titulo,
)

TIMEZONE = ZoneInfo("America/Sao_Paulo")
DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _fmt_hora(evento: dict) -> str:
    start = evento.get("start", {})
    if "dateTime" in start:
        return datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
    return "Dia todo"


def _fmt_data(dt: datetime) -> str:
    return f"{DIAS_PT[dt.weekday()]}, {dt.day:02d}/{dt.month:02d}"


def agenda_hoje() -> str:
    try:
        eventos = listar_eventos_hoje()
    except Exception as e:
        return f"Erro ao buscar agenda: {e}"

    hoje = datetime.now(TIMEZONE)
    header = f"Agenda — {_fmt_data(hoje)}"

    if not eventos:
        return f"{header}\n\nNenhum compromisso hoje."

    linhas = [header, "─" * 28]
    for e in eventos:
        linhas.append(f"{_fmt_hora(e)}  {e.get('summary', 'Sem título')}")
    return "\n".join(linhas)


def agenda_semana() -> str:
    try:
        eventos = listar_eventos_semana()
    except Exception as e:
        return f"Erro ao buscar agenda: {e}"

    if not eventos:
        return "Nenhum compromisso nos próximos 7 dias."

    por_dia: dict = {}
    for e in eventos:
        start = e.get("start", {})
        dt_str = start.get("dateTime") or start.get("date", "")
        dt = datetime.fromisoformat(dt_str)
        chave = dt.strftime("%Y-%m-%d")
        por_dia.setdefault(chave, {"dt": dt, "eventos": []})["eventos"].append(e)

    linhas = ["Agenda — próximos 7 dias", "─" * 28]
    for chave in sorted(por_dia.keys()):
        grupo = por_dia[chave]
        linhas.append(f"\n{_fmt_data(grupo['dt'])}")
        for e in grupo["eventos"]:
            linhas.append(f"  {_fmt_hora(e)}  {e.get('summary', 'Sem título')}")
    return "\n".join(linhas)


def adicionar_compromisso(data_str: str, hora_str: str, titulo: str) -> str:
    try:
        criar_evento(data_str, hora_str, titulo)
        return f"Compromisso criado: {titulo} — {data_str} às {hora_str}"
    except Exception as e:
        return f"Erro ao criar compromisso: {e}"


def remover_compromisso(busca: str) -> str:
    try:
        return deletar_evento_por_titulo(busca)
    except Exception as e:
        return f"Erro ao remover: {e}"
