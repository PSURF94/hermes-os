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
    from services.todoist import criar_tarefa
    tarefa = criar_tarefa(texto)
    missoes = get_missoes()
    missoes.append({"id": tarefa["id"], "content": texto, "is_todoist": True})
    set_missoes(missoes)


def remover(mission_id: str) -> list:
    missoes = [m for m in get_missoes() if m["id"] != mission_id]
    set_missoes(missoes)
    return missoes


def build_keyboard_raw(pendente: list, selecionadas: list) -> list:
    keyboard = []
    for t in pendente:
        check = "✅" if t["id"] in selecionadas else "○"
        due = t.get("due_str", "")
        prefix = f"{due} " if due else ""
        max_chars = 32 - len(prefix)
        nome = t["content"][:max_chars] + ("…" if len(t["content"]) > max_chars else "")
        keyboard.append([{"text": f"{check} {prefix}{nome}", "callback_data": f"ms:toggle:{t['id']}"}])
    n = len(selecionadas)
    keyboard.append([
        {"text": "✏️ Nova missão", "callback_data": "ms:nova"},
        {"text": f"✅ Confirmar ({n})", "callback_data": "ms:confirm"},
    ])
    return keyboard
