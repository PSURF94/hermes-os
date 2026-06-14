from datetime import datetime
from zoneinfo import ZoneInfo

from services.google_calendar import listar_eventos_hoje
from services.todoist import listar_tarefas, listar_projetos_todoist
from services.supabase_client import get_client
from services.estado import get_config, set_config

TIMEZONE = ZoneInfo("America/Sao_Paulo")
DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _fmt_hora(evento: dict) -> str:
    start = evento.get("start", {})
    if "dateTime" in start:
        return datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
    return "Dia todo"


def _projetos_excluidos() -> list[dict]:
    return get_config("briefing_excluir_projetos") or []


def ocultar_projeto(nome: str) -> str:
    try:
        projetos = listar_projetos_todoist()
    except Exception as e:
        return f"Erro ao buscar projetos Todoist: {e}"

    match = next((p for p in projetos if nome.lower() in p.get("name", "").lower()), None)
    if not match:
        nomes = ", ".join(p.get("name", "") for p in projetos)
        return f'Projeto não encontrado. Disponíveis: {nomes}'

    excluidos = _projetos_excluidos()
    if any(p["id"] == match["id"] for p in excluidos):
        return f'"{match["name"]}" já está oculto do briefing.'

    excluidos.append({"id": match["id"], "name": match["name"]})
    set_config("briefing_excluir_projetos", excluidos)
    return f'"{match["name"]}" ocultado do briefing.'


def mostrar_projeto(nome: str) -> str:
    excluidos = _projetos_excluidos()
    match = next((p for p in excluidos if nome.lower() in p.get("name", "").lower()), None)
    if not match:
        if not excluidos:
            return "Nenhum projeto oculto no momento."
        nomes = ", ".join(p["name"] for p in excluidos)
        return f'Projeto não encontrado nos ocultos. Ocultos: {nomes}'

    excluidos = [p for p in excluidos if p["id"] != match["id"]]
    set_config("briefing_excluir_projetos", excluidos)
    return f'"{match["name"]}" voltará a aparecer no briefing.'


def listar_ocultos() -> str:
    excluidos = _projetos_excluidos()
    if not excluidos:
        return "Nenhum projeto oculto no briefing."
    nomes = "\n".join(f"  • {p['name']}" for p in excluidos)
    return f"Projetos ocultos do briefing:\n{nomes}"


def gerar_briefing() -> str:
    hoje = datetime.now(TIMEZONE)
    dia = DIAS_PT[hoje.weekday()]
    data_fmt = f"{dia}, {hoje.day:02d}/{hoje.month:02d}"

    partes = [f"📋 BRIEFING — {data_fmt}", ""]

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
        ids_excluidos = {p["id"] for p in _projetos_excluidos()}
        tarefas = [
            t for t in listar_tarefas()
            if t.get("project_id") not in ids_excluidos
        ]
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

    partes.append("")

    # Projetos
    partes.append("🗂️ PROJETOS")
    try:
        db = get_client()
        result = (
            db.table("projetos")
            .select("nome, proxima_acao")
            .eq("status", "ativo")
            .order("nome")
            .execute()
        )
        if not result.data:
            partes.append("  Nenhum projeto ativo.")
        else:
            for p in result.data:
                acao = p.get("proxima_acao") or "—"
                partes.append(f"  {p['nome']}: {acao}")
    except Exception as e:
        partes.append(f"  Erro: {e}")

    return "\n".join(partes)
