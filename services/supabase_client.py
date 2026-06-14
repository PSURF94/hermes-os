from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    global _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL e SUPABASE_KEY não configurados no .env")
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
