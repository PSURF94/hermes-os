import csv
import io
import httpx
from datetime import date

SHEET_ID = "1WLUpZtzFMAkuVFmnxFkKhrxlhaFvql3K7ivBtHwQoFI"
GID = "675893143"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

DIAS_PT = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def escala_hoje() -> str:
    hoje = date.today()

    try:
        resp = httpx.get(CSV_URL, follow_redirects=True, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return f"  Erro ao buscar escala: {e}"

    rows = [list(row) for row in csv.reader(io.StringIO(resp.text))]

    # Localiza coluna do dia atual na linha de dias do mês (row 1)
    day_row = rows[1] if len(rows) > 1 else []
    col_hoje = None
    for i, v in enumerate(day_row):
        if v.strip() == str(hoje.day):
            col_hoje = i
            break

    if col_hoje is None:
        return f"  Dia {hoje.day} não encontrado na planilha."

    # Total escalados (row 2)
    total_row = rows[2] if len(rows) > 2 else []
    total_str = total_row[col_hoje].strip() if col_hoje < len(total_row) else "?"
    try:
        total = int(total_str)
        status = "✅ OK" if total >= 4 else "⚠️ Abaixo do mínimo operacional"
    except ValueError:
        total = total_str
        status = ""

    # Processa equipes operacionais — para ao encontrar EXPEDIENTE
    servico = []
    missao = []

    for row in rows[8:]:
        if not row:
            continue
        nome = row[0].strip()
        if not nome:
            continue
        if nome.upper().startswith("EXPEDIENTE"):
            break
        if nome.upper().startswith("EQUIPE"):
            continue

        # Forward-fill até col_hoje para lidar com células mescladas
        ultimo_val = ""
        for i in range(3, col_hoje + 1):
            val = row[i].strip() if i < len(row) else ""
            if val:
                ultimo_val = val
        status_hoje = ultimo_val

        if not status_hoje or status_hoje.upper() == "FOLGA":
            continue

        if "MISSÃO" in status_hoje.upper() or "CURSO" in status_hoje.upper():
            missao.append(nome)
        else:
            servico.append(f"{nome} ({status_hoje})")

    # Monta saída
    linhas = [f"  {total} escalados {status}"]
    for s in servico:
        linhas.append(f"  • {s}")
    if missao:
        linhas.append(f"  Missão/Curso: {', '.join(missao)}")
    if not servico and not missao:
        linhas.append("  Sem escalados identificados.")

    return "\n".join(linhas)
