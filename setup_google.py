"""
Rode este script UMA VEZ para autorizar o acesso ao Google Calendar.
O token será salvo no Supabase — não precisa repetir.

Uso: python setup_google.py
"""
import json
from datetime import timezone
from dotenv import load_dotenv

load_dotenv()

from google_auth_oauthlib.flow import InstalledAppFlow
from services.supabase_client import get_client

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    db = get_client()
    db.table("tokens").upsert({"id": "google", "data": token_data}).execute()
    print("Token Google salvo no Supabase com sucesso.")


if __name__ == "__main__":
    main()
