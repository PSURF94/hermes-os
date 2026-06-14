from services.todoist import listar_tarefas, criar_tarefa, concluir_tarefa


def lista_tarefas() -> str:
    try:
        tarefas = listar_tarefas()
    except Exception as e:
        return f"Erro ao buscar tarefas: {e}"

    if not tarefas:
        return "Nenhuma tarefa pendente."

    linhas = [f"Tarefas pendentes ({len(tarefas)})", "─" * 28]
    for t in tarefas:
        linhas.append(f"• {t.get('content', 'Sem título')}")
    return "\n".join(linhas)


def nova_tarefa(titulo: str) -> str:
    try:
        criar_tarefa(titulo)
        return f"Tarefa criada: {titulo}"
    except Exception as e:
        return f"Erro ao criar tarefa: {e}"


def feito(busca: str) -> str:
    try:
        return concluir_tarefa(busca)
    except Exception as e:
        return f"Erro ao concluir: {e}"
