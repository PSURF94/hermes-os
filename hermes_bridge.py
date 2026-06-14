"""
Hermes Bridge — roda no PC em casa.
Lê mensagens pendentes do Supabase, processa com Claude e responde no Telegram.

Uso: python hermes_bridge.py
"""
import os
import time
import subprocess
import httpx
from dotenv import load_dotenv

load_dotenv()

from services.supabase_client import get_client

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
POLL_INTERVAL = 10  # segundos


def send_telegram(chat_id: str, text: str) -> None:
    httpx.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def buscar_contexto() -> str:
    db = get_client()
    projetos = (
        db.table("projetos")
        .select("nome, proxima_acao, objetivo")
        .eq("status", "ativo")
        .execute()
        .data
    )
    linhas = []
    for p in projetos:
        linhas.append(f"- {p['nome']}: {p.get('proxima_acao') or p.get('objetivo') or '—'}")
    return "\n".join(linhas)


def perguntar_claude(pergunta: str) -> str:
    contexto = buscar_contexto()
    prompt = f"""Você é Hermes, assistente pessoal de Paulo Henrique.
Paulo é Tenente dos Bombeiros Militares do ES e trader de futuros (MNQ/NQ).

Projetos ativos:
{contexto}

Responda de forma direta e prática, em português.

Pergunta: {pergunta}"""

    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout.strip() or "Claude não retornou resposta."


def processar():
    db = get_client()
    result = (
        db.table("mensagens")
        .select("*")
        .eq("status", "pendente")
        .order("criado_em")
        .limit(1)
        .execute()
    )
    if not result.data:
        return

    msg = result.data[0]
    mid = msg["id"]
    print(f"→ Processando: {msg['conteudo'][:60]}...")

    db.table("mensagens").update({"status": "processando"}).eq("id", mid).execute()

    try:
        resposta = perguntar_claude(msg["conteudo"])
    except subprocess.TimeoutExpired:
        resposta = "Claude demorou muito para responder. Tente novamente."
    except Exception as e:
        resposta = f"Erro ao processar: {e}"

    db.table("mensagens").update({
        "resposta": resposta,
        "status": "concluido",
    }).eq("id", mid).execute()

    send_telegram(msg["chat_id"], resposta)
    print(f"✓ Respondido: {resposta[:60]}...")


def main():
    print("Hermes Bridge ativo. Aguardando mensagens... (Ctrl+C para parar)\n")
    while True:
        try:
            processar()
        except Exception as e:
            print(f"Erro no loop: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
