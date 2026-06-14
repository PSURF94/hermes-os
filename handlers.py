from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config import TELEGRAM_BOT_TOKEN
from modules.registros import registrar
from modules.agenda import agenda_hoje, agenda_semana, adicionar_compromisso, remover_compromisso
from modules.tarefas import lista_tarefas, nova_tarefa, feito
from modules.projetos import listar_projetos, detalhar_projeto
from modules.exportar import exportar_projeto

AJUDA_TEXT = """<b>Hermes OS</b> — Chefe de Gabinete Pessoal

<b>AGENDA</b>
/agenda — compromissos de hoje
/agenda semana — próximos 7 dias
/agenda adicionar <i>DD/MM HH:MM [título]</i> — criar compromisso
/agenda remover <i>[título parcial]</i> — remover compromisso

<b>TAREFAS</b>
/tarefa <i>[texto]</i> — criar tarefa
/tarefa listar — tarefas pendentes
/feito <i>[id]</i> — marcar como concluída

<b>PROJETOS</b>
/projetos — todos os projetos ativos
/projeto <i>[nome]</i> — detalhes de um projeto

<b>REGISTROS</b>
/ideia <i>[texto]</i> — captura rápida (inbox)
/registrar <i>[texto]</i> — salvar nota

<b>BRIEFING</b>
/briefing — relatório completo do momento

<b>EXPORTAR</b>
/exportar <i>[projeto]</i> — contexto formatado para Claude

<i>Qualquer texto sem comando é salvo automaticamente como nota no inbox.</i>"""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.effective_user.first_name or "Paulo"
    await update.message.reply_html(
        f"Olá, {nome}. Hermes OS ativo.\n\nUse /ajuda para ver os comandos disponíveis."
    )


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(AJUDA_TEXT)


async def cmd_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(agenda_hoje())
    elif args[0] == "semana":
        await update.message.reply_text(agenda_semana())
    elif args[0] == "adicionar":
        if len(args) < 4:
            await update.message.reply_text(
                "Uso: /agenda adicionar DD/MM HH:MM [título]\n"
                "Exemplo: /agenda adicionar 15/06 14:00 Reunião OrganizePJ"
            )
            return
        await update.message.reply_text(
            adicionar_compromisso(args[1], args[2], " ".join(args[3:]))
        )
    elif args[0] == "remover":
        if len(args) < 2:
            await update.message.reply_text("Uso: /agenda remover [título parcial]\nExemplo: /agenda remover Reunião")
            return
        await update.message.reply_text(remover_compromisso(" ".join(args[1:])))
    else:
        await update.message.reply_text("Subcomando não reconhecido. Use /ajuda para ver os comandos disponíveis.")


async def cmd_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Use:\n/tarefa [texto] — criar tarefa\n/tarefa listar — ver pendentes"
        )
    elif args[0] == "listar":
        await update.message.reply_text(lista_tarefas())
    else:
        await update.message.reply_text(nova_tarefa(" ".join(args)))


async def cmd_feito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /feito [título parcial]\nExemplo: /feito reunião")
        return
    await update.message.reply_text(feito(" ".join(args)))


async def cmd_projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_projetos())


async def cmd_projeto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Informe o nome do projeto.\nExemplo: /projeto OrganizePJ")
        return
    await update.message.reply_text(detalhar_projeto(" ".join(args)))


async def cmd_ideia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Informe a ideia.\nExemplo: /ideia Adicionar gráfico de evolução no OrganizePJ")
        return
    texto = " ".join(args)
    try:
        registrar(texto, tipo="ideia", status="inbox")
        await update.message.reply_text(f"Ideia salva no inbox:\n\"{texto}\"")
    except Exception as e:
        await update.message.reply_text(f"Erro ao salvar: {e}")


async def cmd_registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Informe o texto a registrar.\nExemplo: /registrar Decisão: usar Cushion no timeline")
        return
    texto = " ".join(args)
    try:
        registrar(texto, tipo="nota", status="ativo")
        await update.message.reply_text(f"Registrado:\n\"{texto}\"")
    except Exception as e:
        await update.message.reply_text(f"Erro ao salvar: {e}")


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Briefing — disponível na Fase 6 (após Agenda, Tarefas e Projetos).\n\nAinda não implementado.")


async def cmd_exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Informe o projeto.\nExemplo: /exportar OrganizePJ")
        return
    await update.message.reply_text(exportar_projeto(" ".join(args)))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    try:
        registrar(texto, tipo="nota", status="inbox")
        await update.message.reply_text(f"Salvo no inbox:\n\"{texto}\"")
    except Exception as e:
        await update.message.reply_text(f"Erro ao salvar: {e}")


def setup_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("agenda", cmd_agenda))
    app.add_handler(CommandHandler("tarefa", cmd_tarefa))
    app.add_handler(CommandHandler("feito", cmd_feito))
    app.add_handler(CommandHandler("projetos", cmd_projetos))
    app.add_handler(CommandHandler("projeto", cmd_projeto))
    app.add_handler(CommandHandler("ideia", cmd_ideia))
    app.add_handler(CommandHandler("registrar", cmd_registrar))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("exportar", cmd_exportar))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app
