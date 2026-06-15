import httpx
from datetime import date, timedelta
from urllib.parse import quote

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# Vitória, ES
_LAT = -20.3155
_LON = -40.3128

_WMO: dict[int, tuple[str, str]] = {
    0:  ("☀️", "Céu limpo"),
    1:  ("🌤️", "Poucas nuvens"),
    2:  ("🌤️", "Parcialmente nublado"),
    3:  ("☁️",  "Nublado"),
    45: ("🌫️", "Névoa"),
    48: ("🌫️", "Névoa com geada"),
    51: ("🌦️", "Chuvisco leve"),
    53: ("🌦️", "Chuvisco moderado"),
    55: ("🌦️", "Chuvisco intenso"),
    61: ("🌧️", "Chuva leve"),
    63: ("🌧️", "Chuva moderada"),
    65: ("🌧️", "Chuva intensa"),
    80: ("🌧️", "Pancadas de chuva"),
    81: ("⛈️", "Pancadas fortes"),
    82: ("⛈️", "Pancadas muito fortes"),
    95: ("⛈️", "Trovoada"),
    96: ("⛈️", "Trovoada com granizo"),
    99: ("⛈️", "Trovoada severa"),
}


def _url_boletim(d: date, rev: int = 0) -> str:
    mes = MESES_PT[d.month]
    path = (
        f"/Media/AlertaES/Boletins/Boletim Meteorológico"
        f"/{d.year}/{d.month:02d}-{mes}"
        f"/BAMES-{d.year}{d.month:02d}{d.day:02d}.{rev}.pdf"
    )
    return "https://alerta.es.gov.br" + quote(path, safe="/")


def _bames_mais_recente() -> tuple[str, str] | tuple[None, None]:
    hoje = date.today()
    for delta in range(3):
        d = hoje - timedelta(days=delta)
        for rev in (1, 0):
            url = _url_boletim(d, rev)
            try:
                resp = httpx.head(url, follow_redirects=True, timeout=8)
                if resp.status_code == 200:
                    sufixo = " rev.1" if rev == 1 else ""
                    return url, f"BAMES {d.day:02d}/{d.month:02d}{sufixo}"
            except Exception:
                continue
    return None, None


def boletim_mais_recente() -> str:
    linhas: list[str] = []

    try:
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": _LAT,
                "longitude": _LON,
                "daily": "temperature_2m_max,temperature_2m_min,"
                         "precipitation_probability_max,weathercode",
                "timezone": "America/Sao_Paulo",
                "forecast_days": 1,
            },
            timeout=8,
        )
        resp.raise_for_status()
        daily = resp.json()["daily"]
        code = daily["weathercode"][0]
        emoji, descricao = _WMO.get(code, ("🌡️", "—"))
        tmax = daily["temperature_2m_max"][0]
        tmin = daily["temperature_2m_min"][0]
        chuva = daily["precipitation_probability_max"][0]
        linhas.append(f"  {emoji} {descricao}")
        linhas.append(f"  🌡️ {tmin:.0f}°C – {tmax:.0f}°C  |  🌧️ Chuva: {chuva}%")
    except Exception:
        linhas.append("  Dados climáticos indisponíveis.")

    url, label = _bames_mais_recente()
    if url:
        linhas.append(f'  📄 <a href="{url}">{label}</a>')

    return "\n".join(linhas)
