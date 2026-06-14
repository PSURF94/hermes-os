from services.supabase_client import get_client


def listar_projetos() -> str:
    db = get_client()
    result = db.table("projetos").select("nome, proxima_acao, status").eq("status", "ativo").order("nome").execute()

    if not result.data:
        return "Nenhum projeto cadastrado."

    linhas = [f"Projetos ativos ({len(result.data)})", "─" * 28]
    for p in result.data:
        acao = p.get("proxima_acao") or "—"
        linhas.append(f"\n{p['nome']}\n  → {acao}")
    return "\n".join(linhas)


def detalhar_projeto(busca: str) -> str:
    db = get_client()
    result = db.table("projetos").select("*").ilike("nome", f"%{busca}%").execute()

    if not result.data:
        return f'Projeto "{busca}" não encontrado.'

    p = result.data[0]
    ctx = db.table("contexto_projetos").select("*").eq("projeto_nome", p["nome"]).order("criado_em", desc=True).execute()

    pendencias = [c["conteudo"] for c in ctx.data if c["tipo"] == "pendencia"]
    decisoes   = [c["conteudo"] for c in ctx.data if c["tipo"] == "decisao"]
    notas      = [c["conteudo"] for c in ctx.data if c["tipo"] == "nota"]

    linhas = [
        f"Projeto: {p['nome']}",
        "─" * 28,
        f"Objetivo: {p.get('objetivo') or '—'}",
        f"Próxima ação: {p.get('proxima_acao') or '—'}",
        f"Atualizado: {p.get('ultima_atualizacao') or '—'}",
    ]

    if pendencias:
        linhas.append("\nPendências:")
        for c in pendencias:
            linhas.append(f"  • {c}")

    if decisoes:
        linhas.append("\nDecisões recentes:")
        for c in decisoes[:5]:
            linhas.append(f"  • {c}")

    if notas:
        linhas.append("\nNotas:")
        for c in notas[:3]:
            linhas.append(f"  • {c}")

    return "\n".join(linhas)
