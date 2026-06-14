from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

from config import TELEGRAM_BOT_TOKEN
from modules.registros import registrar
from modules.agenda import agenda_hoje, agenda_semana, adicionar_compromisso, remover_compromisso
from modules.tarefas import lista_tarefas, nova_tarefa, feito
from modules.projetos import listar_projetos, detalhar_projeto
from modules.exportar import exportar_projeto
from modules.briefing import gerar_briefing
from modules.insights import get_tags, salvar_pendente, confirmar_tag, listar_insights

AJUDA_TEXT = """<b>Hermes OS</b> — Chefe de Gabinete Pessoal

<b>AGENDA</b> — Google Calendar
/agenda — compromissos de hoje
/agenda semana — próximos 7 dias
/agenda adicionar <i>DD/MM HH:MM [título]</i> — criar compromisso
/agenda remover <i>[título parcial]</i> — remover compromisso

<b>TAREFAS</b> — Todoist
/tarefa <i>[texto]</i> — criar tarefa
/tarefa listar — tarefas pendentes
/feito <i>[título parcial]</i> — marcar como concluída

<b>PROJETOS</b> — Supabase
/projetos — todos os projetos ativos com próxima ação
/projeto <i>[nome]</i> — detalhes, pendências e decisões

<b>INSIGHTS</b>
/insight <i>[texto]</i> — capturar insight (selecione a tag por botão)
/insight_tag <i>[tag]</i> — definir tag de insight pendente
/insights <i>[tag]</i> — listar insights por tag

<b>REGISTROS</b>
/ideia <i>[texto]</i> — captura rápida para o inbox
/registrar <i>[texto]</i> — salvar nota processada

<b>BRIEFING</b>
/briefing — agenda + tarefas + projetos num só lugar

<b>EXPORTAR</b>
/exportar <i>[projeto]</i> — contexto formatado para colar no Claude

<i>Texto livre → salvo automaticamente no inbox.</i>"""


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


async def cmd_insight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Uso: /insight [texto]\nExemplo: /insight gap de abertura consistente acima de 10pts"
        )
        return

    texto = " ".join(context.args)
    salvar_pendente(texto)

    tags = get_tags()
    keyboard: list[list] = []
    row: list = []
    for tag in tags:
        row.append(InlineKeyboardButton(tag, callback_data=f"i:{tag}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("+ Nova tag", callback_data="i:__nova__")])

    preview = texto[:60] + ("..." if len(texto) > 60 else "")
    await update.message.reply_text(
        f"\"{preview}\"\n\nSelecione a tag:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def callback_insight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tag = query.data[2:]  # remove prefixo "i:"

    if tag == "__nova__":
        await query.edit_message_text(
            "Use /insight_tag [nome da tag] para salvar o insight pendente.\n"
            "Exemplo: /insight_tag FinançasTudo"
        )
        return

    msg = confirmar_tag(tag)
    await query.edit_message_text(msg)


async def cmd_insight_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /insight_tag [nome da tag]\nExemplo: /insight_tag FinançasTudo")
        return
    tag = " ".join(context.args)
    await update.message.reply_text(confirmar_tag(tag))


async def cmd_insights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag = " ".join(context.args) if context.args else None
    await update.message.reply_text(listar_insights(tag))


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
    await update.message.reply_text(gerar_briefing())


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
    app.add_handler(CommandHandler("insight", cmd_insight))
    app.add_handler(CommandHandler("insight_tag", cmd_insight_tag))
    app.add_handler(CommandHandler("insights", cmd_insights))
    app.add_handler(CommandHandler("ideia", cmd_ideia))
    app.add_handler(CommandHandler("registrar", cmd_registrar))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("exportar", cmd_exportar))
    app.add_handler(CallbackQueryHandler(callback_insight, pattern=r"^i:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app
