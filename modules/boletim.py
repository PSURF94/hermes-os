import httpx
from datetime import date, timedelta
from urllib.parse import quote

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}


def _url_boletim(d: date, rev: int = 0) -> str:
    mes = MESES_PT[d.month]
    path = (
        f"/Media/AlertaES/Boletins/Boletim Meteorológico"
        f"/{d.year}/{d.month:02d}-{mes}"
        f"/BAMES-{d.year}{d.month:02d}{d.day:02d}.{rev}.pdf"
    )
    return "https://alerta.es.gov.br" + quote(path, safe="/")


def boletim_mais_recente() -> str:
    hoje = date.today()
    for delta in range(3):
        d = hoje - timedelta(days=delta)
        for rev in (1, 0):
            url = _url_boletim(d, rev)
            try:
                resp = httpx.head(url, follow_redirects=True, timeout=8)
                if resp.status_code == 200:
                    sufixo = " (rev.1)" if rev == 1 else ""
                    return f"  BAMES {d.day:02d}/{d.month:02d}/{d.year}{sufixo}\n  {url}"
            except Exception:
                continue
    return "  Boletim não disponível no momento."
