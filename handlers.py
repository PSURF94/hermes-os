import asyncio
import re
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)
from services.whisper import transcrever

from config import TELEGRAM_BOT_TOKEN as _TOKEN
from modules.gemini_chat import chat as gemini_chat, analyze_image as gemini_image
from modules.registros import registrar
from modules.agenda import agenda_hoje, agenda_semana, adicionar_compromisso, remover_compromisso
from modules.tarefas import lista_tarefas, nova_tarefa, feito
from services.todoist import ETIQUETAS_VALIDAS, concluir_por_id as _concluir_por_id
from modules.missoes_dia import (
    get_missoes, get_pendente, get_selecionadas, toggle, confirmar,
    adicionar_manual, remover, build_keyboard_raw,
)
from modules.briefing import gerar_briefing
from services.estado import get_estado, set_estado
from services.supabase_client import get_client

AJUDA_TEXT = """<b>Hermes OS</b> — Chefe de Gabinete Pessoal

<b>AGENDA</b>
/agenda — compromissos de hoje
/agenda semana — próximos 7 dias
/agenda adicionar <i>DD/MM HH:MM título</i> — criar compromisso
/agenda remover <i>título parcial</i> — remover compromisso

<b>TAREFAS</b>
/tarefa <i>texto #oper|#adm|#renda|#pessoal</i> — criar tarefa com etiqueta
/tarefa listar — todas as tarefas pendentes
/tarefa listar <i>#etiqueta</i> — filtrar por etiqueta
/feito <i>título parcial</i> — marcar como concluída

<b>MISSÕES DO DIA</b>
/missao <i>texto</i> — define uma missão do dia (salva no Todoist com #missao)
Às 16h você recebe um check-in com botões para marcar como feito.

<b>REGISTROS</b>
/ideia <i>texto</i> — captura rápida para o inbox
/registrar <i>texto</i> — salva nota processada

<b>BRIEFING</b>
/briefing — agenda + tarefas num só lugar

<b>TEXTO LIVRE</b>
Qualquer mensagem → Hermes responde com IA (Gemini)
Texto com <i>#etiqueta</i> → confirma criação de tarefa automaticamente

<b>VOZ</b>
Áudio → transcrito via Whisper → Hermes responde com IA

<b>FOTOS</b>
Foto → Hermes analisa com IA
Foto com legenda → legenda é a instrução de análise

<b>AUTOMÁTICO</b>
Resenha matinal às 07h: clima · escala CERD · agenda · tarefas"""


TAREFA_CONFIRM_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Criar tarefa", callback_data="t:criar"),
        InlineKeyboardButton("📋 Outras opções", callback_data="t:outros"),
    ]
])

CLASSIFICAR_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Tarefa",       callback_data="c:tarefa"),
        InlineKeyboardButton("📅 Compromisso", callback_data="c:compromisso"),
        InlineKeyboardButton("📝 Nota",        callback_data="c:nota"),
    ],
])



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
        await update.message.reply_text("Qual a tarefa? Use #oper, #adm, #renda ou #pessoal para categorizar.")
    elif args[0] == "listar":
        label = None
        resto = " ".join(args[1:])
        m = re.search(r"#(\w+)", resto)
        if m:
            label = m.group(1).lower()
        await update.message.reply_text(lista_tarefas(label))
    else:
        await update.message.reply_text(nova_tarefa(" ".join(args)))


async def cmd_feito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        lista = lista_tarefas()
        set_estado("feito")
        await update.message.reply_text(f"{lista}\n\n─────────────\nQual tarefa concluir? (título parcial)")
        return
    await update.message.reply_text(feito(" ".join(args)))



async def callback_tarefa_detect(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await query.edit_message_text("Entrada não encontrada.")
        return

    rid = result.data[0]["id"]
    texto = result.data[0]["conteudo"]

    if acao == "criar":
        db.table("registros").delete().eq("id", rid).execute()
        await query.edit_message_text(nova_tarefa(texto))

    elif acao == "outros":
        preview = texto[:80] + ("..." if len(texto) > 80 else "")
        await query.edit_message_text(
            f"\"{preview}\"\n\nO que fazer com isso?",
            reply_markup=CLASSIFICAR_KEYBOARD,
        )


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


def _ptb_keyboard(raw: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(b["text"], callback_data=b["callback_data"]) for b in row]
        for row in raw
    ])


async def callback_selecao_missao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acao = query.data[3:]  # after "ms:"

    if acao.startswith("toggle:"):
        task_id = acao[7:]
        ids = toggle(task_id)
        pendente = get_pendente()
        kb = _ptb_keyboard(build_keyboard_raw(pendente, ids))
        await query.edit_message_reply_markup(reply_markup=kb)

    elif acao == "nova":
        set_estado("missao_manual")
        await query.answer("Digite a missão no chat", show_alert=False)
        await query.message.reply_text("Digite a missão que deseja adicionar:")

    elif acao == "confirm":
        missoes = confirmar()
        if not missoes:
            await query.edit_message_text("Nenhuma missão selecionada. Use /missao para adicionar depois.")
        else:
            linhas = ["🎯 <b>Missões de hoje definidas:</b>\n"]
            for m in missoes:
                linhas.append(f"  → {m['content']}")
            await query.edit_message_text("\n".join(linhas), parse_mode="HTML")


async def callback_checkin_missao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    acao = query.data[2:]  # after "m:"

    if acao.startswith("close:"):
        task_id = acao[6:]
        try:
            missoes_restantes = remover(task_id)
            # fecha no Todoist se for tarefa real
            missoes_todas = get_missoes()
            era_todoist = next((m for m in missoes_todas if m["id"] == task_id and m.get("is_todoist")), None)
            if era_todoist:
                _concluir_por_id(task_id)
        except Exception:
            pass
        missoes_restantes = get_missoes()
        if not missoes_restantes:
            await query.edit_message_text("✅ Todas as missões concluídas! Ótimo dia, Paulo!")
        else:
            linhas = ["🎯 <b>Missões do dia — como foi?</b>\n"]
            for m in missoes_restantes:
                linhas.append(f"• {m['content']}")
            keyboard = []
            for m in missoes_restantes:
                nome = m["content"][:28] + ("…" if len(m["content"]) > 28 else "")
                keyboard.append([{"text": f"✅ {nome}", "callback_data": f"m:close:{m['id']}"}])
            if len(missoes_restantes) > 1:
                keyboard.append([{"text": "✅ Todas feitas", "callback_data": "m:all"}])
            await query.edit_message_text(
                "\n".join(linhas),
                parse_mode="HTML",
                reply_markup=_ptb_keyboard(keyboard),
            )

    elif acao == "all":
        missoes = get_missoes()
        for m in missoes:
            if m.get("is_todoist"):
                try:
                    _concluir_por_id(m["id"])
                except Exception:
                    pass
        from modules.missoes_dia import set_missoes
        set_missoes([])
        await query.edit_message_text("✅ Todas as missões concluídas! Ótimo dia, Paulo!")


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_briefing())



async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    estado = get_estado()

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

    if estado == "missao_manual":
        set_estado(None)
        adicionar_manual(texto)
        missoes = get_missoes()
        linhas = ["🎯 <b>Missões de hoje:</b>\n"]
        for m in missoes:
            linhas.append(f"  → {m['content']}")
        await update.message.reply_html("\n".join(linhas))
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

    # detecta #etiqueta válida → confirmação de tarefa
    tag_match = re.search(r"#(\w+)", texto)
    if tag_match and tag_match.group(1).lower() in ETIQUETAS_VALIDAS:
        tag = tag_match.group(1).lower()
        titulo_limpo = re.sub(r"\s*#\w+", "", texto).strip()
        try:
            await asyncio.gather(
                update.message.reply_text(
                    f"Criar tarefa \"{titulo_limpo}\" #{tag}?",
                    reply_markup=TAREFA_CONFIRM_KEYBOARD,
                ),
                asyncio.to_thread(registrar, texto, tipo="rascunho", status="classificar"),
            )
        except Exception as e:
            await update.message.reply_text(f"Erro: {e}")
        return

    # texto livre → Gemini
    msg = await update.message.reply_text("...")
    try:
        resposta = await asyncio.to_thread(gemini_chat, texto)
        await msg.edit_text(resposta)
    except Exception as e:
        await msg.edit_text(f"Erro ao processar: {e}")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = update.message.caption or "Descreva o que vê nesta imagem."
    msg = await update.message.reply_text("Analisando imagem...")
    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        imagem_bytes = bytes(await file.download_as_bytearray())
    except Exception as e:
        await msg.edit_text(f"Erro ao baixar imagem: {e}")
        return

    try:
        resposta = await asyncio.to_thread(gemini_image, imagem_bytes, prompt)
        await msg.edit_text(resposta)
    except Exception as e:
        await msg.edit_text(f"Erro ao analisar imagem: {e}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Transcrevendo áudio...")
    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        audio_bytes = bytes(await file.download_as_bytearray())
        texto = transcrever(audio_bytes)
    except Exception as e:
        await msg.edit_text(f"Erro na transcrição: {e}")
        return

    await msg.edit_text(f"Você disse: \"{texto}\"\n\nProcessando...")
    try:
        resposta = await asyncio.to_thread(gemini_chat, texto)
        await msg.edit_text(f"Você disse: \"{texto}\"\n\n{resposta}")
    except Exception as e:
        await msg.edit_text(f"Você disse: \"{texto}\"\n\nErro ao processar: {e}")


def setup_application() -> Application:
    app = Application.builder().token(_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(CommandHandler("agenda", cmd_agenda))
    app.add_handler(CommandHandler("tarefa", cmd_tarefa))
    app.add_handler(CommandHandler("feito", cmd_feito))
    app.add_handler(CommandHandler("ideia", cmd_ideia))
    app.add_handler(CommandHandler("registrar", cmd_registrar))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CallbackQueryHandler(callback_tarefa_detect, pattern=r"^t:"))
    app.add_handler(CallbackQueryHandler(callback_classificar, pattern=r"^c:"))
    app.add_handler(CallbackQueryHandler(callback_selecao_missao, pattern=r"^ms:"))
    app.add_handler(CallbackQueryHandler(callback_checkin_missao, pattern=r"^m:"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app
