from services.supabase_client import get_client


def get_tags() -> list[str]:
    db = get_client()
    result = (
        db.table("registros")
        .select("projeto")
        .eq("tipo", "insight")
        .eq("status", "ativo")
        .order("projeto")
        .execute()
    )
    return sorted({r["projeto"] for r in result.data if r.get("projeto")})


def salvar_pendente(conteudo: str) -> None:
    db = get_client()
    db.table("registros").insert({
        "tipo": "insight",
        "conteudo": conteudo,
        "status": "pendente",
    }).execute()


def confirmar_tag(tag: str) -> str:
    db = get_client()
    result = (
        db.table("registros")
        .select("id, conteudo")
        .eq("tipo", "insight")
        .eq("status", "pendente")
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return "Nenhum insight pendente encontrado."
    r = result.data[0]
    db.table("registros").update({"projeto": tag, "status": "ativo"}).eq("id", r["id"]).execute()
    return f"Insight salvo em {tag}:\n\"{r['conteudo']}\""


def listar_insights(tag: str | None = None) -> str:
    db = get_client()
    query = (
        db.table("registros")
        .select("projeto, conteudo")
        .eq("tipo", "insight")
        .eq("status", "ativo")
        .order("criado_em", desc=True)
    )
    if tag:
        query = query.ilike("projeto", f"%{tag}%")
    result = query.limit(20).execute()

    if not result.data:
        filtro = f" em '{tag}'" if tag else ""
        return f"Nenhum insight{filtro} registrado."

    agrupado: dict = {}
    for r in result.data:
        proj = r.get("projeto") or "Sem tag"
        agrupado.setdefault(proj, []).append(r["conteudo"])

    linhas = [f"Insights{' — ' + tag if tag else ''}", "─" * 28]
    for proj, itens in agrupado.items():
        linhas.append(f"\n{proj}")
        for item in itens:
            texto = item[:100] + ("..." if len(item) > 100 else "")
            linhas.append(f"  • {texto}")
    return "\n".join(linhas)
