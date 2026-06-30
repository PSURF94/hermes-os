from datetime import datetime
from zoneinfo import ZoneInfo

from services.google_calendar import listar_eventos_hoje
from services.todoist import listar_tarefas, get_inbox_project_id
from modules.missoes_dia import get_missoes

TIMEZONE = ZoneInfo("America/Sao_Paulo")
DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _fmt_hora(evento: dict) -> str:
    start = evento.get("start", {})
    if "dateTime" in start:
        return datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
    return "Dia todo"


def gerar_briefing() -> str:
    hoje = datetime.now(TIMEZONE)
    dia = DIAS_PT[hoje.weekday()]
    data_fmt = f"{dia}, {hoje.day:02d}/{hoje.month:02d}"

    partes = [f"📋 BRIEFING — {data_fmt}", ""]

    # Missões do dia
    try:
        missoes = get_missoes()
        if missoes:
            partes.append("🎯 MISSÕES DE HOJE")
            for m in missoes:
                partes.append(f"  → {m['content']}")
            partes.append("")
    except Exception:
        pass

    # Agenda
    partes.append("📅 AGENDA")
    try:
        eventos = listar_eventos_hoje()
        if not eventos:
            partes.append("  Nenhum compromisso hoje.")
        else:
            for e in eventos:
                partes.append(f"  {_fmt_hora(e)}  {e.get('summary', 'Sem título')}")
    except Exception as e:
        partes.append(f"  Erro: {e}")

    partes.append("")

    # Tarefas
    partes.append("✅ TAREFAS")
    try:
        inbox_id = get_inbox_project_id()
        todas = listar_tarefas()
        tarefas = [t for t in todas if t.get("project_id") == inbox_id] if inbox_id else todas
        if not tarefas:
            partes.append("  Nenhuma tarefa pendente.")
        else:
            partes.append(f"  {len(tarefas)} pendente(s):")
            for t in tarefas[:7]:
                partes.append(f"  • {t.get('content', 'Sem título')}")
            if len(tarefas) > 7:
                partes.append(f"  ...e mais {len(tarefas) - 7}")
    except Exception as e:
        partes.append(f"  Erro: {e}")

    return "\n".join(partes)
