from datetime import datetime
from zoneinfo import ZoneInfo

from services.google_calendar import listar_eventos_hoje
from services.todoist import listar_tarefas
from services.supabase_client import get_client

TIMEZONE = ZoneInfo("America/Sao_Paulo")
DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _fmt_hora(evento: dict) -> str:
    start = evento.get("start", {})
    if "dateTime" in start:
        return datetime.fromisoformat(start["dateTime"]).strftime("%H:%M")
    return "Dia todo"


def gerar_resenha() -> str:
    hoje = datetime.now(TIMEZONE)
    dia = DIAS_PT[hoje.weekday()]
    data_fmt = f"{dia}, {hoje.day:02d}/{hoje.month:02d}"

    partes = [f"☀️ Bom dia, Paulo! Resenha de {data_fmt}", ""]

    # Agenda
    partes.append("📅 AGENDA HOJE")
    try:
        eventos = listar_eventos_hoje()
        if not eventos:
            partes.append("  Sem compromissos.")
        else:
            for e in eventos:
                partes.append(f"  {_fmt_hora(e)}  {e.get('summary', 'Sem título')}")
    except Exception as e:
        partes.append(f"  Erro: {e}")

    partes.append("")

    # Tarefas
    partes.append("✅ TAREFAS PENDENTES")
    try:
        tarefas = listar_tarefas()
        if not tarefas:
            partes.append("  Nenhuma.")
        else:
            for t in tarefas[:5]:
                partes.append(f"  • {t.get('content', '')}")
            if len(tarefas) > 5:
                partes.append(f"  ...e mais {len(tarefas) - 5}")
    except Exception as e:
        partes.append(f"  Erro: {e}")

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
                acao = p.get("proxima_acao") or "—"
                partes.append(f"  {p['nome']}: {acao}")
    except Exception as e:
        partes.append(f"  Erro: {e}")

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
                tag = r.get("projeto") or "geral"
                texto = r["conteudo"]
                linha = f"  [{tag}] {texto[:90]}{'...' if len(texto) > 90 else ''}"
                partes.append(linha)
    except Exception as e:
        partes.append(f"  Erro: {e}")

    return "\n".join(partes)
