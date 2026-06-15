import html as _html
from datetime import datetime
from zoneinfo import ZoneInfo

from services.google_calendar import listar_eventos_hoje
from services.todoist import listar_tarefas, listar_projetos_todoist
from services.supabase_client import get_client
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


def _e(s: str) -> str:
    return _html.escape(str(s))


def gerar_resenha() -> str:
    hoje = datetime.now(TIMEZONE)
    dia = DIAS_PT[hoje.weekday()]
    data_fmt = f"{dia}, {hoje.day:02d}/{hoje.month:02d}"

    partes = [f"☀️ Bom dia, Paulo! Resenha de {data_fmt}", ""]

    # Boletim meteorológico
    partes.append("🌤️ BOLETIM METEOROLÓGICO")
    partes.append(boletim_mais_recente())
    partes.append("")

    # Escala CERD
    partes.append("🚒 ESCALA CERD")
    partes.append(escala_hoje())
    partes.append("")

    # Agenda
    partes.append("📅 AGENDA HOJE")
    try:
        eventos = listar_eventos_hoje()
        if not eventos:
            partes.append("  Sem compromissos.")
        else:
            for e in eventos:
                partes.append(f"  {_fmt_hora(e)}  {_e(e.get('summary', 'Sem título'))}")
    except Exception as e:
        partes.append(f"  Erro: {_e(e)}")

    partes.append("")

    # Tarefas
    partes.append("✅ TAREFAS PENDENTES")
    try:
        try:
            projetos_todoist = listar_projetos_todoist()
            ids_excluidos = {p["id"] for p in projetos_todoist if p.get("name") in PROJETOS_OCULTOS_BRIEFING}
        except Exception:
            ids_excluidos = set()
        tarefas = [t for t in listar_tarefas() if t.get("project_id") not in ids_excluidos]
        if not tarefas:
            partes.append("  Nenhuma.")
        else:
            for t in tarefas[:5]:
                partes.append(f"  • {_e(t.get('content', ''))}")
            if len(tarefas) > 5:
                partes.append(f"  ...e mais {len(tarefas) - 5}")
    except Exception as e:
        partes.append(f"  Erro: {_e(e)}")

    partes.append("")

    # Projetos
    partes.append("🗂️ PROJETOS — PRÓXIMA AÇÃO")
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
                acao = _e(p.get("proxima_acao") or "—")
                partes.append(f"  {_e(p['nome'])}: {acao}")
    except Exception as e:
        partes.append(f"  Erro: {_e(e)}")

    partes.append("")

    # Insights recentes
    partes.append("💡 INSIGHTS RECENTES")
    try:
        db = get_client()
        result = (
            db.table("registros")
            .select("projeto, conteudo")
            .eq("tipo", "insight")
            .eq("status", "ativo")
            .order("criado_em", desc=True)
            .limit(5)
            .execute()
        )
        if not result.data:
            partes.append("  Nenhum insight recente.")
        else:
            for r in result.data:
                tag = _e(r.get("projeto") or "geral")
                texto_raw = r["conteudo"]
                texto = _e(texto_raw[:90]) + ("..." if len(texto_raw) > 90 else "")
                partes.append(f"  [{tag}] {texto}")
    except Exception as e:
        partes.append(f"  Erro: {_e(e)}")

    return "\n".join(partes)
