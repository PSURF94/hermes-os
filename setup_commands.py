"""
Registra os comandos do bot no Telegram.
Rodar uma vez — depois o app já sugere os comandos ao digitar /.
"""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from telegram import Bot, BotCommand
from config import TELEGRAM_BOT_TOKEN

COMMANDS = [
    BotCommand("briefing",     "Resumo diário — agenda + tarefas + projetos"),
    BotCommand("agenda",       "Compromissos de hoje"),
    BotCommand("tarefa",       "Criar tarefa ou listar pendentes"),
    BotCommand("feito",        "Marcar tarefa como concluída"),
    BotCommand("insight",      "Capturar insight com tag"),
    BotCommand("insights",     "Listar insights salvos"),
    BotCommand("projetos",     "Listar projetos ativos"),
    BotCommand("projeto",      "Detalhes de um projeto"),
    BotCommand("exportar",     "Exportar contexto para colar no Claude"),
    BotCommand("ideia",        "Captura rápida para o inbox"),
    BotCommand("registrar",    "Salvar nota processada"),
    BotCommand("reply",        "Responder ao Claude em tarefa"),
    BotCommand("ajuda",        "Ver todos os comandos"),
]

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    await bot.set_my_commands(COMMANDS)
    print("Comandos registrados com sucesso!")
    for c in COMMANDS:
        print(f"  /{c.command:15} {c.description}")

asyncio.run(main())
