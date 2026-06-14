import re
from services.todoist import listar_tarefas, criar_tarefa, concluir_tarefa, ETIQUETAS_VALIDAS


def _extrair_label(texto: str) -> tuple[str, str | None]:
    match = re.search(r"#(\w+)", texto)
    if match:
        tag = match.group(1).lower()
        if tag in ETIQUETAS_VALIDAS:
            texto_limpo = re.sub(r"\s*#\w+", "", texto).strip()
            return texto_limpo, tag
    return texto, None


def lista_tarefas(label: str | None = None) -> str:
    try:
        tarefas = listar_tarefas(label)
    except Exception as e:
        return f"Erro ao buscar tarefas: {e}"

    filtro = f" [{label}]" if label else ""
    if not tarefas:
        return f"Nenhuma tarefa pendente{filtro}."

    linhas = [f"Tarefas pendentes{filtro} ({len(tarefas)})", "─" * 28]
    for t in tarefas:
        tags = t.get("labels", [])
        tag_str = f" #{tags[0]}" if tags else ""
        linhas.append(f"• {t.get('content', 'Sem título')}{tag_str}")
    return "\n".join(linhas)


def nova_tarefa(titulo: str) -> str:
    texto, label = _extrair_label(titulo)
    try:
        criar_tarefa(texto, label)
        tag_str = f" #{label}" if label else ""
        return f"Tarefa criada: {texto}{tag_str}"
    except Exception as e:
        return f"Erro ao criar tarefa: {e}"


def feito(busca: str) -> str:
    try:
        return concluir_tarefa(busca)
    except Exception as e:
        return f"Erro ao concluir: {e}"
