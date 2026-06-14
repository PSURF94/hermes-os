from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from services.supabase_client import get_client

TIMEZONE = ZoneInfo("America/Sao_Paulo")


def _get_service():
    db = get_client()
    result = db.table("tokens").select("data").eq("id", "google").execute()
    if not result.data:
        raise ValueError("Google Calendar não autorizado. Execute setup_google.py primeiro.")

    td = result.data[0]["data"]
    creds = Credentials(
        token=td["token"],
        refresh_token=td["refresh_token"],
        token_uri=td["token_uri"],
        client_id=td["client_id"],
        client_secret=td["client_secret"],
        scopes=td["scopes"],
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        td["token"] = creds.token
        td["expiry"] = creds.expiry.isoformat() if creds.expiry else None
        db.table("tokens").update({
            "data": td,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", "google").execute()

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def listar_eventos(time_min: datetime, time_max: datetime) -> list:
    service = _get_service()
    result = service.events().list(
        calendarId="primary",
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    return result.get("items", [])


def listar_eventos_hoje() -> list:
    now = datetime.now(TIMEZONE)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=0)
    return listar_eventos(start, end)


def listar_eventos_semana() -> list:
    now = datetime.now(TIMEZONE)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return listar_eventos(start, end)


def criar_evento(data_str: str, hora_str: str, titulo: str, duracao_min: int = 60) -> dict:
    """data_str: DD/MM ou DD/MM/AAAA | hora_str: HH:MM"""
    service = _get_service()
    hoje = datetime.now(TIMEZONE)

    parts = data_str.split("/")
    dia, mes = int(parts[0]), int(parts[1])
    ano = int(parts[2]) if len(parts) == 3 else hoje.year

    h, m = map(int, hora_str.split(":"))
    start_dt = datetime(ano, mes, dia, h, m, tzinfo=TIMEZONE)
    end_dt = start_dt + timedelta(minutes=duracao_min)

    evento = {
        "summary": titulo,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Sao_Paulo"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "America/Sao_Paulo"},
    }
    return service.events().insert(calendarId="primary", body=evento).execute()


def deletar_evento_por_titulo(busca: str) -> str:
    """Busca por título (hoje e próximos 7 dias) e deleta o primeiro match."""
    service = _get_service()
    eventos = listar_eventos_semana()
    match = next(
        (e for e in eventos if busca.lower() in e.get("summary", "").lower()), None
    )
    if not match:
        return f'Nenhum evento encontrado com "{busca}".'
    service.events().delete(calendarId="primary", eventId=match["id"]).execute()
    return f'Removido: {match.get("summary")}'
