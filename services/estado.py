from services.supabase_client import get_client


def get_estado() -> str | None:
    db = get_client()
    r = db.table("estado_bot").select("aguardando").eq("id", 1).execute()
    return r.data[0].get("aguardando") if r.data else None


def set_estado(aguardando: str | None) -> None:
    db = get_client()
    db.table("estado_bot").update({"aguardando": aguardando}).eq("id", 1).execute()
