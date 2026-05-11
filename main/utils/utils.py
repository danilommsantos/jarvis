import requests


def formatar_tempo(segundos):
    segundos = int(segundos)

    dias, resto = divmod(segundos, 86400)   # 24*60*60
    horas, resto = divmod(resto, 3600)
    minutos, segundos = divmod(resto, 60)

    # Se tem dias
    if dias > 0:
        dia_txt = "dia" if dias == 1 else "dias"
        return f"{dias} {dia_txt} {horas:02}:{minutos:02}:{segundos:02}"

    # Se não tem dias, mas tem horas
    if horas > 0:
        return f"{horas:02}:{minutos:02}:{segundos:02}"

    # Só minutos e segundos
    return f"{minutos:02}:{segundos:02}"


def buscar_pecas_btv(nup_formatado):
    """
    Consulta a API do BTV e retorna a lista de peças bruta.
    """
    url = f"http://pecas.ml-prd.rede.tst/api/v1/processos/{nup_formatado}/pecas"
    try:
        # Timeout curto para não travar o carregamento da página de revisão
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("pecas", [])
    except Exception:
        return None # Retorna None em caso de erro ou timeout
    return None