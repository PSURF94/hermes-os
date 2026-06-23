import html as _html
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

from services.google_calendar import listar_eventos_hoje
from services.todoist import listar_tarefas, listar_projetos_todoist
from modules.briefing import PROJETOS_OCULTOS_BRIEFING
from modules.boletim import boletim_mais_recente
from modules.escala import escala_hoje

TIMEZONE = ZoneInfo("America/Sao_Paulo")
DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _fmt_hora(evento: dict) -> str:
    start = evento.get("start", {})
    if "dateTime" in start:
        return datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
    return "Dia todo"


def _e(s) -> str:
    return _html.escape(str(s))


def _get_tarefas_filtradas() -> list:
    try:
        projetos = listar_projetos_todoist()
        ids_excluidos = {p["id"] for p in projetos if p.get("name") in PROJETOS_OCULTOS_BRIEFING}
    except Exception:
        ids_excluidos = set()
    tarefas = listar_tarefas()
    # exclui projetos ocultos e missões (missões têm seção própria)
    return [
        t for t in tarefas
        if t.get("project_id") not in ids_excluidos
        and "missao" not in t.get("labels", [])
    ]


def gerar_resenha() -> str:
    hoje = datetime.now(TIMEZONE)
    dia = DIAS_PT[hoje.weekday()]
    data_fmt = f"{dia}, {hoje.day:02d}/{hoje.month:02d}"

    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_boletim  = ex.submit(boletim_mais_recente)
        fut_escala   = ex.submit(escala_hoje)
        fut_eventos  = ex.submit(listar_eventos_hoje)
        fut_tarefas  = ex.submit(_get_tarefas_filtradas)

        def safe(fut, fallback):
            try:
                return fut.result(timeout=20)
            except Exception as e:
                return fallback(e)

        boletim_txt = safe(fut_boletim, lambda e: f"  Indisponível: {_e(e)}")
        escala_txt  = safe(fut_escala,  lambda e: f"  Indisponível: {_e(e)}")
        eventos     = safe(fut_eventos, lambda _: [])
        tarefas     = safe(fut_tarefas, lambda _: [])

    partes = [f"☀️ Bom dia, Paulo! Resenha de {data_fmt}", ""]

    # Boletim
    partes += ["🌤️ BOLETIM METEOROLÓGICO", boletim_txt, ""]

    # Escala
    partes += ["🚒 ESCALA CERD", escala_txt, ""]

    # Agenda
    partes.append("📅 AGENDA HOJE")
    if not eventos:
        partes.append("  Sem compromissos.")
    else:
        for e in eventos:
            partes.append(f"  {_fmt_hora(e)}  {_e(e.get('summary', 'Sem título'))}")
    partes.append("")

    # Tarefas
    partes.append("✅ TAREFAS PENDENTES")
    if not tarefas:
        partes.append("  Nenhuma.")
    else:
        for t in tarefas[:5]:
            partes.append(f"  • {_e(t.get('content', ''))}")
        if len(tarefas) > 5:
            partes.append(f"  ...e mais {len(tarefas) - 5}")

    return "\n".join(partes)
