import pandas as pd
import re

def limpar_data_excel(data_valor):
    if pd.isna(data_valor) or str(data_valor).lower() == 'nan':
        return None
    # Converte para string e pega apenas a parte da data (AAAA-MM-DD)
    return str(data_valor).split(' ')[0]

def separar_itens_celula(texto):
    """O algoritmo de separação que discutimos (cada linha é um item)"""
    if not texto or pd.isna(texto):
        return []
    # Divide por quebra de linha, limpa espaços e remove duplicatas
    itens = [i.strip() for i in str(texto).split('\n') if i.strip()]
    return list(dict.fromkeys(itens))

def extrair_autor_obs(texto_obs):
    """Sua regra: Por 'NOME'."""
    if not texto_obs or pd.isna(texto_obs):
        return None, ""
    match = re.search(r"Por '([^']+)'\.(.*)", str(texto_obs), re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, str(texto_obs)