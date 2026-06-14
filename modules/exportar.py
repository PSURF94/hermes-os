from datetime import date
from services.supabase_client import get_client


def exportar_projeto(busca: str) -> str:
    db = get_client()
    result = db.table("projetos").select("*").ilike("nome", f"%{busca}%").execute()

    if not result.data:
        return f'Projeto "{busca}" não encontrado.'

    p = result.data[0]
    ctx = db.table("contexto_projetos").select("*").eq("projeto_nome", p["nome"]).order("criado_em", desc=True).execute()

    pendencias = [c["conteudo"] for c in ctx.data if c["tipo"] == "pendencia"]
    decisoes   = [c["conteudo"] for c in ctx.data if c["tipo"] == "decisao"]
    notas      = [c["conteudo"] for c in ctx.data if c["tipo"] == "nota"]

    hoje = date.today().strftime("%d/%m/%Y")
    linhas = [
        f"=== CONTEXTO — {p['nome']} ({hoje}) ===",
        "",
        f"OBJETIVO:",
        f"{p.get('objetivo') or '—'}",
        "",
        f"STATUS: {p.get('status') or '—'}",
        f"PRÓXIMA AÇÃO: {p.get('proxima_acao') or '—'}",
    ]

    if pendencias:
        linhas.append("\nPENDÊNCIAS:")
        for c in pendencias:
            linhas.append(f"• {c}")

    if decisoes:
        linhas.append("\nDECISÕES RECENTES:")
        for c in decisoes[:5]:
            linhas.append(f"• {c}")

    if notas:
        linhas.append("\nNOTAS:")
        for c in notas[:3]:
            linhas.append(f"• {c}")

    linhas += ["", "Cole este bloco no Claude para contexto imediato.", "==="]
    return "\n".join(linhas)
