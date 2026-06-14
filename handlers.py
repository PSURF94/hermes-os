from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from services.whisper import transcrever

from config import TELEGRAM_BOT_TOKEN
from modules.registros import registrar
from modules.agenda import agenda_hoje, agenda_semana, adicionar_compromisso, remover_compromisso
from modules.tarefas import lista_tarefas, nova_tarefa, feito
from modules.projetos import listar_projetos, detalhar_projeto
from modules.exportar import exportar_projeto
from modules.briefing import gerar_briefing
from modules.insights import get_tags, salvar_pendente, confirmar_tag, listar_insights
from services.estado import get_estado, set_estado
from services.supabase_client import get_client

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
/insight — capturar insight (bot pergunta o texto e a tag)
/insights — listar insights (bot pergunta a tag)

<b>REGISTROS</b>
/ideia <i>[texto]</i> — captura rápida para o inbox
/registrar <i>[texto]</i> — salvar nota processada

<b>BRIEFING</b>
/briefing — agenda + tarefas + projetos num só lugar

<b>EXPORTAR</b>
/exportar <i>[projeto]</i> — contexto formatado para colar no Claude

<i>Texto livre → salvo automaticamente no inbox.</i>"""


CLASSIFICAR_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Insight",      callback_data="c:insight"),
        InlineKeyboardButton("Tarefa",       callback_data="c:tarefa"),
    ],
    [
        InlineKeyboardButton("Compromisso",  callback_data="c:compromisso"),
        InlineKeyboardButton("Nota",         callback_data="c:nota"),
    ],
    [
        InlineKeyboardButton("→ Claude",     callback_data="c:claude"),
    ],
])


def _tag_keyboard(tags: list[str]) -> InlineKeyboardMarkup:
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
    return InlineKeyboardMarkup(keyboard)


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
            await update.message.reply_text("Uso: /agenda remover [título parcial]")
            return
        await update.message.reply_text(remover_compromisso(" ".join(args[1:])))
    else:
        await update.message.reply_text("Subcomando não reconhecido. Use /ajuda.")


async def cmd_tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        set_estado("tarefa")
        await update.message.reply_text("Qual a tarefa?")
    elif args[0] == "listar":
        await update.message.reply_text(lista_tarefas())
    else:
        await update.message.reply_text(nova_tarefa(" ".join(args)))


async def cmd_feito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        set_estado("feito")
        await update.message.reply_text("Qual tarefa concluir? (título parcial)")
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
        set_estado("insight")
        await update.message.reply_text("Qual o insight?")
        return

    texto = " ".join(context.args)
    salvar_pendente(texto)
    preview = texto[:60] + ("..." if len(texto) > 60 else "")
    await update.message.reply_text(
        f"\"{preview}\"\n\nSelecione a tag:",
        reply_markup=_tag_keyboard(get_tags()),
    )


async def cmd_insight_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /insight_tag [nome da tag]")
        return
    await update.message.reply_text(confirmar_tag(" ".join(context.args)))


async def cmd_insights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(listar_insights(None))
        return
    await update.message.reply_text(listar_insights(" ".join(context.args)))


async def callback_insight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tag = query.data[2:]

    if tag == "__nova__":
        set_estado("nova_tag")
        await query.edit_message_text("Qual o nome da nova tag?")
        return

    await query.edit_message_text(confirmar_tag(tag))


async def callback_classificar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    acao = query.data[2:]
    db = get_client()

    result = (
        db.table("registros")
        .select("id, conteudo")
        .eq("status", "classificar")
        .order("criado_em", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        await query.edit_message_text("Nenhuma entrada pendente encontrada.")
        return

    rid = result.data[0]["id"]
    texto = result.data[0]["conteudo"]

    if acao == "nota":
        db.table("registros").update({"tipo": "nota", "status": "ativo"}).eq("id", rid).execute()
        await query.edit_message_text(f"Nota salva:\n\"{texto}\"")

    elif acao == "tarefa":
        nova_tarefa(texto)
        db.table("registros").delete().eq("id", rid).execute()
        await query.edit_message_text(f"Tarefa criada:\n\"{texto}\"")

    elif acao == "compromisso":
        set_estado("compromisso_data")
        await query.edit_message_text(
            f"Compromisso: \"{texto[:60]}\"\n\nData e hora? (DD/MM HH:MM)\nExemplo: 18/06 15:00"
        )

    elif acao == "insight":
        db.table("registros").update({"tipo": "insight", "status": "pendente"}).eq("id", rid).execute()
        preview = texto[:60] + ("..." if len(texto) > 60 else "")
        await query.edit_message_text(
            f"\"{preview}\"\n\nSelecione a tag:",
            reply_markup=_tag_keyboard(get_tags()),
        )

    elif acao == "claude":
        chat_id = str(query.message.chat_id)
        db.table("registros").delete().eq("id", rid).execute()
        db.table("mensagens").insert({
            "conteudo": texto,
            "status": "pendente",
            "chat_id": chat_id,
        }).execute()
        preview = texto[:60] + ("..." if len(texto) > 60 else "")
        await query.edit_message_text(f"Enviado ao Claude:\n\"{preview}\"\n\nAguardando resposta...")


async def cmd_ideia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        set_estado("ideia")
        await update.message.reply_text("Qual a ideia?")
        return
    texto = " ".join(context.args)
    try:
        registrar(texto, tipo="ideia", status="inbox")
        await update.message.reply_text(f"Ideia salva:\n\"{texto}\"")
    except Exception as e:
        await update.message.reply_text(f"Erro ao salvar: {e}")


async def cmd_registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        set_estado("registrar")
        await update.message.reply_text("O que registrar?")
        return
    texto = " ".join(context.args)
    try:
        registrar(texto, tipo="nota", status="ativo")
        await update.message.reply_text(f"Registrado:\n\"{texto}\"")
    except Exception as e:
        await update.message.reply_text(f"Erro ao salvar: {e}")


async def cmd_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        set_estado("reply")
        await update.message.reply_text("Qual sua resposta para o Claude?")
        return
    texto = " ".join(context.args)
    try:
        get_client().table("respostas_claude").insert({"conteudo": texto}).execute()
        await update.message.reply_text(f"Resposta enviada ao Claude:\n\"{texto}\"")
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")


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
    estado = get_estado()

    if estado == "reply":
        set_estado(None)
        try:
            get_client().table("respostas_claude").insert({"conteudo": texto}).execute()
            await update.message.reply_text(f"Resposta enviada ao Claude:\n\"{texto}\"")
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")
        return

    if estado == "insight":
        set_estado(None)
        salvar_pendente(texto)
        preview = texto[:60] + ("..." if len(texto) > 60 else "")
        await update.message.reply_text(
            f"\"{preview}\"\n\nSelecione a tag:",
            reply_markup=_tag_keyboard(get_tags()),
        )
        return

    if estado == "nova_tag":
        set_estado(None)
        await update.message.reply_text(confirmar_tag(texto))
        return

    if estado == "compromisso_data":
        partes = texto.strip().split()
        if len(partes) < 2:
            await update.message.reply_text("Formato inválido. Use: DD/MM HH:MM\nExemplo: 18/06 15:00")
            return
        data_str, hora_str = partes[0], partes[1]
        result = (
            get_client()
            .table("registros")
            .select("id, conteudo")
            .eq("status", "classificar")
            .order("criado_em", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            await update.message.reply_text("Entrada original não encontrada.")
            set_estado(None)
            return
        rid = result.data[0]["id"]
        titulo = result.data[0]["conteudo"]
        set_estado(None)
        get_client().table("registros").delete().eq("id", rid).execute()
        await update.message.reply_text(adicionar_compromisso(data_str, hora_str, titulo))
        return

    if estado == "tarefa":
        set_estado(None)
        await update.message.reply_text(nova_tarefa(texto))
        return

    if estado == "feito":
        set_estado(None)
        await update.message.reply_text(feito(texto))
        return

    if estado == "ideia":
        set_estado(None)
        try:
            registrar(texto, tipo="ideia", status="inbox")
            await update.message.reply_text(f"Ideia salva:\n\"{texto}\"")
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")
        return

    if estado == "registrar":
        set_estado(None)
        try:
            registrar(texto, tipo="nota", status="ativo")
            await update.message.reply_text(f"Registrado:\n\"{texto}\"")
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")
        return

    if estado == "reply":
        set_estado(None)
        try:
            get_client().table("respostas_claude").insert({"conteudo": texto}).execute()
            await update.message.reply_text(f"Resposta enviada ao Claude:\n\"{texto}\"")
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")
        return

    # sem estado: perguntar o que fazer
    try:
        registrar(texto, tipo="rascunho", status="classificar")
        preview = texto[:80] + ("..." if len(texto) > 80 else "")
        await update.message.reply_text(
            f"\"{preview}\"\n\nO que fazer com isso?",
            reply_markup=CLASSIFICAR_KEYBOARD,
        )
    except Exception as e:
        await update.message.reply_text(f"Erro: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    await update.message.reply_text("Transcrevendo áudio...")

    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        audio_bytes = bytes(await file.download_as_bytearray())
        texto = transcrever(audio_bytes)
    except Exception as e:
        await update.message.reply_text(f"Erro na transcrição: {e}")
        return

    # Se Claude está aguardando resposta, redireciona para respostas_claude
    estado = get_estado()
    if estado == "reply":
        set_estado(None)
        get_client().table("respostas_claude").insert({"conteudo": texto}).execute()
        await update.message.reply_text(f"Resposta enviada ao Claude:\n\"{texto}\"")
        return

    try:
        get_client().table("mensagens").insert({
            "conteudo": texto,
            "status": "pendente",
            "chat_id": chat_id,
        }).execute()
    except Exception as e:
        await update.message.reply_text(f"Erro ao salvar: {e}")
        return

    await update.message.reply_text(
        f"Entendido: \"{texto}\"\n\nAguardando Claude..."
    )


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
    app.add_handler(CommandHandler("insights", cmd_insights))
    app.add_handler(CommandHandler("ideia", cmd_ideia))
    app.add_handler(CommandHandler("registrar", cmd_registrar))
    app.add_handler(CommandHandler("reply", cmd_reply))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("exportar", cmd_exportar))
    app.add_handler(CallbackQueryHandler(callback_classificar, pattern=r"^c:"))
    app.add_handler(CallbackQueryHandler(callback_insight, pattern=r"^i:"))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app
