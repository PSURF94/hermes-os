from config import TELEGRAM_BOT_TOKEN
from handlers import setup_application


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN não encontrado. Verifique o arquivo .env")

    app = setup_application()
    print("Hermes OS iniciado (polling — modo local)...")
    app.run_polling()


if __name__ == "__main__":
    main()
