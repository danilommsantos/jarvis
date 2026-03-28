import pandas as pd
import re
from django.contrib.auth.models import User
from django.utils.text import slugify
from ..models import Responsavel

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


from django.contrib.auth.models import User
from ..models import Responsavel

def obter_ou_criar_responsavel(nome_bruto):
    """
    Exemplo: 'DANILO MULLER MARTINS SANTOS'
    -> User(username='danilo.santos', first_name='danilo', last_name='santos')
    -> Responsavel(nome_completo='DANILO MULLER MARTINS SANTOS')
    """
    if not nome_bruto or str(nome_bruto).lower() in ['nan', 'None', '']:
        return None

    nome_original = str(nome_bruto).strip()
    partes = nome_original.split()
    
    # Lógica de nomes em minúsculas
    primeiro_nome = partes[0].lower()
    ultimo_nome = partes[-1].lower() if len(partes) > 1 else ""
    
    # Gerar username: nome.sobrenome
    username_gerado = f"{primeiro_nome}.{ultimo_nome}" if ultimo_nome else primeiro_nome

    # 1. Busca ou cria o User padrão do Django
    user, created = User.objects.get_or_create(
        username=username_gerado,
        defaults={
            'first_name': primeiro_nome,
            'last_name': ultimo_nome,
        }
    )

    # 2. Busca ou cria o modelo Responsavel vinculado ao User
    responsavel, r_created = Responsavel.objects.get_or_create(
        user=user,
        defaults={'nome_completo': nome_original}
    )

    # Se o nome completo na planilha mudou, atualizamos o registro
    if not r_created and responsavel.nome_completo != nome_original:
        responsavel.nome_completo = nome_original
        responsavel.save()

    return responsavel


def formatar_numero_processo(texto_bruto):
    """
    Separa a fase do número e formata o NUP.
    Ex: 'Ag-AIRR - 00000010920235220109' -> ('Ag-AIRR', '0000001-09.2023.5.22.0109')
    """
    if not texto_bruto or " - " not in str(texto_bruto):
        return "INDETERMINADO", str(texto_bruto)
    
    try:
        partes = str(texto_bruto).split(" - ", 1)
        fase = partes[0].strip()
        numero_sujo = partes[1].strip()
        
        # Usa a biblioteca nup que você já conhece
        numero_formatado = nup(numero_sujo).formatado()
        return fase, numero_formatado
    except Exception:
        return "ERRO_FORMATO", str(texto_bruto)