import uuid
from services.estado import get_config, set_config


def get_missoes() -> list:
    return get_config("missoes_dia") or []


def set_missoes(missoes: list) -> None:
    set_config("missoes_dia", missoes)


def get_pendente() -> list:
    return get_config("ms_pendente") or []


def set_pendente(tarefas: list) -> None:
    set_config("ms_pendente", tarefas)


def get_selecionadas() -> list:
    return get_config("ms_selecionadas") or []


def toggle(task_id: str) -> list:
    ids = get_selecionadas()
    if task_id in ids:
        ids.remove(task_id)
    else:
        ids.append(task_id)
    set_config("ms_selecionadas", ids)
    return ids


def confirmar() -> list:
    pendente = get_pendente()
    ids = get_selecionadas()
    missoes = [
        {"id": t["id"], "content": t["content"], "is_todoist": True}
        for t in pendente if t["id"] in ids
    ]
    set_missoes(missoes)
    set_config("ms_pendente", [])
    set_config("ms_selecionadas", [])
    return missoes


def adicionar_manual(texto: str) -> None:
    missoes = get_missoes()
    missoes.append({"id": f"m_{uuid.uuid4().hex[:8]}", "content": texto, "is_todoist": False})
    set_missoes(missoes)


def remover(mission_id: str) -> list:
    missoes = [m for m in get_missoes() if m["id"] != mission_id]
    set_missoes(missoes)
    return missoes


def build_keyboard_raw(pendente: list, selecionadas: list) -> list:
    keyboard = []
    for t in pendente:
        check = "✅" if t["id"] in selecionadas else "○"
        nome = t["content"][:28] + ("…" if len(t["content"]) > 28 else "")
        keyboard.append([{"text": f"{check} {nome}", "callback_data": f"ms:toggle:{t['id']}"}])
    n = len(selecionadas)
    keyboard.append([
        {"text": "✏️ Nova missão", "callback_data": "ms:nova"},
        {"text": f"✅ Confirmar ({n})", "callback_data": "ms:confirm"},
    ])
    return keyboard
