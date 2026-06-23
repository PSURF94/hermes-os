import os
import base64
from datetime import datetime
import httpx
from services.estado import get_config, set_config
from modules.agenda import (
    agenda_hoje as _agenda_hoje,
    agenda_semana as _agenda_semana,
    adicionar_compromisso as _adicionar_compromisso,
    remover_compromisso as _remover_compromisso,
)
from modules.tarefas import lista_tarefas as _lista_tarefas, nova_tarefa as _nova_tarefa, feito as _feito
from services.todoist import criar_missao as _criar_missao, listar_missoes as _listar_missoes
from modules.briefing import gerar_briefing as _gerar_briefing
from modules.registros import registrar as _registrar

_KEY = os.getenv("GEMINI_API_KEY", "").lstrip('﻿').strip()
_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# ── Tool schemas ──────────────────────────────────────────────────────────────

_TOOL_DEFS = [
    {
        "name": "get_agenda_hoje",
        "description": "Retorna os compromissos de hoje do usuário.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "get_agenda_semana",
        "description": "Retorna os compromissos dos próximos 7 dias.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "criar_compromisso",
        "description": "Cria um compromisso no calendário.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "data":   {"type": "STRING", "description": "Data formato DD/MM"},
                "hora":   {"type": "STRING", "description": "Hora formato HH:MM"},
                "titulo": {"type": "STRING", "description": "Título do compromisso"},
            },
            "required": ["data", "hora", "titulo"],
        },
    },
    {
        "name": "remover_compromisso",
        "description": "Remove um compromisso pelo título parcial.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"titulo": {"type": "STRING", "description": "Título parcial"}},
            "required": ["titulo"],
        },
    },
    {
        "name": "criar_tarefa",
        "description": "Cria uma tarefa. Use #oper, #adm, #renda ou #pessoal. Ex: 'Ligar cliente #adm'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"texto": {"type": "STRING", "description": "Texto da tarefa com #etiqueta"}},
            "required": ["texto"],
        },
    },
    {
        "name": "listar_tarefas",
        "description": "Lista tarefas pendentes. etiqueta opcional: oper, adm, renda, pessoal.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"etiqueta": {"type": "STRING", "description": "Filtro de etiqueta (opcional)"}},
        },
    },
    {
        "name": "concluir_tarefa",
        "description": "Marca uma tarefa como concluída pelo título parcial.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"titulo": {"type": "STRING", "description": "Título parcial da tarefa"}},
            "required": ["titulo"],
        },
    },
    {
        "name": "get_briefing",
        "description": "Retorna o briefing completo: agenda + tarefas.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "criar_missao",
        "description": "Define uma missão do dia — aparece na resenha matinal e no check-in das 16h.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"texto": {"type": "STRING", "description": "Descrição da missão"}},
            "required": ["texto"],
        },
    },
    {
        "name": "listar_missoes",
        "description": "Lista as missões do dia pendentes.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "salvar_nota",
        "description": "Salva uma nota ou ideia rápida.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"texto": {"type": "STRING", "description": "Conteúdo da nota"}},
            "required": ["texto"],
        },
    },
]

# ── Tool runner ───────────────────────────────────────────────────────────────

def _run_tool(name: str, args: dict) -> str:
    try:
        if name == "get_agenda_hoje":       return _agenda_hoje()
        if name == "get_agenda_semana":     return _agenda_semana()
        if name == "criar_compromisso":     return _adicionar_compromisso(args["data"], args["hora"], args["titulo"])
        if name == "remover_compromisso":   return _remover_compromisso(args["titulo"])
        if name == "criar_tarefa":          return _nova_tarefa(args["texto"])
        if name == "listar_tarefas":        return _lista_tarefas(args.get("etiqueta") or None)
        if name == "concluir_tarefa":       return _feito(args["titulo"])
        if name == "get_briefing":          return _gerar_briefing()
        if name == "criar_missao":
            _criar_missao(args["texto"])
            return f"Missão adicionada: \"{args['texto']}\""
        if name == "listar_missoes":
            missoes = _listar_missoes()
            if not missoes:
                return "Nenhuma missão definida para hoje."
            return "\n".join(f"• {m['content']}" for m in missoes)
        if name == "salvar_nota":
            _registrar(args["texto"], tipo="nota", status="ativo")
            return "Nota salva."
        return f"Tool '{name}' desconhecida."
    except Exception as e:
        return f"Erro em {name}: {e}"


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = (
    "Você é Hermes, chefe de gabinete pessoal de Paulo Henrique. "
    "Gerencie agenda, tarefas e registros de forma direta e objetiva. "
    "Use as tools para agir imediatamente — não peça confirmação desnecessária. "
    "Responda sempre em português brasileiro. "
    "Para código, deploy ou análises técnicas complexas, informe que isso requer o Claude Code no PC."
)

# ── History ───────────────────────────────────────────────────────────────────

def _load_history() -> list:
    hist = get_config("historico_conversa")
    return hist if isinstance(hist, list) else []


def _save_history(contents: list) -> None:
    clean = []
    for c in contents:
        texts = [p for p in c.get("parts", []) if "text" in p]
        if texts:
            clean.append({"role": c["role"], "parts": texts})
    set_config("historico_conversa", clean[-16:])


# ── API call ──────────────────────────────────────────────────────────────────

def _call(contents: list, with_tools: bool = True) -> dict:
    payload: dict = {
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "contents": contents,
    }
    if with_tools:
        payload["tools"] = [{"function_declarations": _TOOL_DEFS}]
    resp = httpx.post(f"{_URL}?key={_KEY}", json=payload, timeout=25)
    if not resp.is_success:
        raise Exception(f"Gemini {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# ── Public API ────────────────────────────────────────────────────────────────

def chat(texto: str) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    contents = _load_history() + [
        {"role": "user", "parts": [{"text": f"[{agora}] {texto}"}]}
    ]

    parts: list = []
    for _ in range(5):
        data = _call(contents)
        parts = data["candidates"][0]["content"]["parts"]

        fc_parts = [p for p in parts if "functionCall" in p]
        if not fc_parts:
            contents.append({"role": "model", "parts": parts})
            break

        contents.append({"role": "model", "parts": parts})
        fn_responses = [
            {
                "functionResponse": {
                    "name": p["functionCall"]["name"],
                    "response": {"result": _run_tool(p["functionCall"]["name"], p["functionCall"].get("args", {}))},
                }
            }
            for p in fc_parts
        ]
        contents.append({"role": "user", "parts": fn_responses})

    _save_history(contents)
    return _extract_text(parts)


def _extract_text(parts: list) -> str:
    for p in reversed(parts):
        if "text" in p and not p.get("thought"):
            return p["text"]
    return "Não obtive resposta."


def analyze_image(imagem_bytes: bytes, prompt: str = "Descreva o que vê nesta imagem.") -> str:
    b64 = base64.b64encode(imagem_bytes).decode()
    contents = [{
        "role": "user",
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
        ],
    }]
    try:
        data = _call(contents, with_tools=False)
        parts = data["candidates"][0]["content"]["parts"]
        return _extract_text(parts)
    except Exception as e:
        return f"Erro ao analisar imagem: {e}"
