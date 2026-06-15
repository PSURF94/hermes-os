import html as _html
from concurrent.futures import ThreadPoolExecutor
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


def _e(s) -> str:
    return _html.escape(str(s))


def _get_tarefas_filtradas() -> list:
    try:
        projetos = listar_projetos_todoist()
        ids_excluidos = {p["id"] for p in projetos if p.get("name") in PROJETOS_OCULTOS_BRIEFING}
    except Exception:
        ids_excluidos = set()
    return [t for t in listar_tarefas() if t.get("project_id") not in ids_excluidos]


def _get_projetos_ativos() -> list:
    db = get_client()
    r = db.table("projetos").select("nome, proxima_acao").eq("status", "ativo").order("nome").execute()
    return r.data or []


def _get_insights() -> list:
    db = get_client()
    r = (
        db.table("registros")
        .select("projeto, conteudo")
        .eq("tipo", "insight")
        .eq("status", "ativo")
        .order("criado_em", desc=True)
        .limit(5)
        .execute()
    )
    return r.data or []


def gerar_resenha() -> str:
    hoje = datetime.now(TIMEZONE)
    dia = DIAS_PT[hoje.weekday()]
    data_fmt = f"{dia}, {hoje.day:02d}/{hoje.month:02d}"

    # Busca todos os dados em paralelo
    with ThreadPoolExecutor(max_workers=6) as ex:
        fut_boletim   = ex.submit(boletim_mais_recente)
        fut_escala    = ex.submit(escala_hoje)
        fut_eventos   = ex.submit(listar_eventos_hoje)
        fut_tarefas   = ex.submit(_get_tarefas_filtradas)
        fut_projetos  = ex.submit(_get_projetos_ativos)
        fut_insights  = ex.submit(_get_insights)

        def safe(fut, fallback):
            try:
                return fut.result(timeout=20)
            except Exception as e:
                return fallback(e)

        boletim_txt  = safe(fut_boletim,  lambda e: f"  Indisponível: {_e(e)}")
        escala_txt   = safe(fut_escala,   lambda e: f"  Indisponível: {_e(e)}")
        eventos      = safe(fut_eventos,  lambda _: [])
        tarefas      = safe(fut_tarefas,  lambda _: [])
        projetos_data = safe(fut_projetos, lambda _: [])
        insights_data = safe(fut_insights, lambda _: [])

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
    partes.append("")

    # Projetos
    partes.append("🗂️ PROJETOS — PRÓXIMA AÇÃO")
    if not projetos_data:
        partes.append("  Nenhum projeto ativo.")
    else:
        for p in projetos_data:
            partes.append(f"  {_e(p['nome'])}: {_e(p.get('proxima_acao') or '—')}")
    partes.append("")

    # Insights
    partes.append("💡 INSIGHTS RECENTES")
    if not insights_data:
        partes.append("  Nenhum insight recente.")
    else:
        for r in insights_data:
            tag = _e(r.get("projeto") or "geral")
            raw = r["conteudo"]
            texto = _e(raw[:90]) + ("..." if len(raw) > 90 else "")
            partes.append(f"  [{tag}] {texto}")

    return "\n".join(partes)
