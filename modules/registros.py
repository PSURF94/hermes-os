from services.supabase_client import get_client


def registrar(conteudo: str, tipo: str = "nota", projeto: str | None = None, status: str = "inbox") -> dict:
    db = get_client()
    row = {"tipo": tipo, "conteudo": conteudo, "status": status}
    if projeto:
        row["projeto"] = projeto
    result = db.table("registros").insert(row).execute()
    return result.data[0] if result.data else {}


def listar_registros(status: str | None = None, tipo: str | None = None, limite: int = 10) -> list:
    db = get_client()
    query = db.table("registros").select("*").order("criado_em", desc=True).limit(limite)
    if status:
        query = query.eq("status", status)
    if tipo:
        query = query.eq("tipo", tipo)
    return query.execute().data


def ultimo_registro() -> dict | None:
    db = get_client()
    result = db.table("registros").select("*").order("criado_em", desc=True).limit(1).execute()
    return result.data[0] if result.data else None
