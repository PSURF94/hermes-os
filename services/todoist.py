import os
import httpx

TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")
BASE = "https://api.todoist.com/api/v1"
ETIQUETAS_VALIDAS = {"oper", "adm", "renda", "pessoal"}


def _headers() -> dict:
    if not TODOIST_TOKEN:
        raise ValueError("TODOIST_API_TOKEN não configurado no .env")
    return {"Authorization": f"Bearer {TODOIST_TOKEN}"}


def listar_tarefas(label: str | None = None) -> list:
    params = {}
    if label:
        params["filter"] = f"@{label}"
    todas = []
    while True:
        resp = httpx.get(f"{BASE}/tasks", headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            todas.extend(data.get("results") or data.get("items") or [])
            cursor = data.get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor
        else:
            todas.extend(data)
            break
    return todas


def criar_tarefa(titulo: str, label: str | None = None) -> dict:
    body: dict = {"content": titulo}
    if label:
        body["labels"] = [label]
    resp = httpx.post(f"{BASE}/tasks", headers=_headers(), json=body)
    resp.raise_for_status()
    return resp.json()


def listar_projetos_todoist() -> list:
    resp = httpx.get(f"{BASE}/projects", headers=_headers())
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return data.get("results") or data.get("items") or []
    return data


def get_inbox_project_id() -> str | None:
    try:
        projetos = listar_projetos_todoist()
        inbox = next((p for p in projetos if p.get("is_inbox_project")), None)
        return inbox["id"] if inbox else None
    except Exception:
        return None


def concluir_por_id(task_id: str) -> None:
    resp = httpx.post(f"{BASE}/tasks/{task_id}/close", headers=_headers())
    resp.raise_for_status()


def concluir_tarefa(busca: str) -> str:
    tarefas = listar_tarefas()
    match = next((t for t in tarefas if busca.lower() in t.get("content", "").lower()), None)
    if not match:
        return f'Nenhuma tarefa encontrada com "{busca}".'
    resp = httpx.post(f"{BASE}/tasks/{match['id']}/close", headers=_headers())
    resp.raise_for_status()
    return f'Concluída: {match["content"]}'
