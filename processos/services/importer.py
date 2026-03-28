import pandas as pd
from django.db import transaction
from django.contrib.auth.models import User
from ..models import (
    Processo, Advogado, Parte, OrgaoJulgador, 
    TipoMinuta, SituacaoMinuta, MovimentacaoInterna, 
    Classe, Assunto, Responsavel
)
from .parser import (
    separar_itens_celula, 
    limpar_data_excel, 
    extrair_autor_obs,
    obter_ou_criar_responsavel,
    formatar_numero_processo # Aquela que usa a lib nup
)

def processar_atualizacao_acervo(caminho_arquivo):
    """
    Orquestrador principal: Lê o Excel, limpa os dados e salva no banco.
    """
    # Carrega o Excel (usando openpyxl como engine)
    df = pd.read_excel(caminho_arquivo)
    
    # Usamos transaction.atomic para que, se houver erro em uma linha, 
    # o banco não fique com dados incompletos.
    with transaction.atomic():
        for _, row in df.iterrows():
            # 1. Trata Identificação (Número e Fase)
            fase_extraida, num_formatado = formatar_numero_processo(row.get('Processo Completo'))
            data_ent = limpar_data_excel(row.get('Entrada'))
            
            # 2. Trata o Responsável do Processo (O dono da linha)
            nome_resp_planilha = row.get('Responsável')
            user_responsavel = obter_ou_criar_responsavel(nome_resp_planilha)

            # 3. Trata a Observação e o Responsável pela Nota
            texto_obs_bruto = row.get('Observações')
            nome_autor_obs, texto_obs_limpo = extrair_autor_obs(texto_obs_bruto)
            user_autor_obs = obter_ou_criar_responsavel(nome_autor_obs)

            # 4. Busca ou Cria as FKs (Foreign Keys) simples
            orgao, _ = OrgaoJulgador.objects.get_or_create(nome=str(row.get('Orgão Julgador Colegiado', '')).strip())
            classe, _ = Classe.objects.get_or_create(nome=str(row.get('Classe', '')).strip())
            mov_interna, _ = MovimentacaoInterna.objects.get_or_create(nome=str(row.get('Movimentação Interna', '')).strip())
            sit_minuta, _ = SituacaoMinuta.objects.get_or_create(nome=str(row.get('Situação Minuta', '')).strip())

            # 5. Criar ou Atualizar o Processo (Regra de Unicidade: Número + Data Entrada)
            processo, created = Processo.objects.update_or_create(
                numero=num_formatado,
                data_entrada=data_ent,
                defaults={
                    'fase_completa': fase_extraida,
                    'responsavel': user_responsavel,
                    'orgao_julgador': orgao,
                    'classe': classe,
                    'movimentacao_interna': mov_interna,
                    'situacao_minuta': sit_minuta,
                    'andamento': str(row.get('Andamento', '')).strip(),
                    'movimentacoes': str(row.get('Movimentações', '')).strip(),
                    'obs': texto_obs_limpo,
                    'obs_responsavel': user_autor_obs,
                }
            )

            # 6. Relacionamentos Muitos-para-Muitos (M2M) - Limpando duplicatas do CSV
            
            # Advogados
            advogados_list = separar_itens_celula(row.get('Advogados'))
            for nome_adv in advogados_list:
                adv, _ = Advogado.objects.get_or_create(nome=nome_adv)
                processo.advogados.add(adv)

            # Partes Autoras
            autores_list = separar_itens_celula(row.get('Partes Autoras'))
            for nome_parte in autores_list:
                p, _ = Parte.objects.get_or_create(nome=nome_parte)
                processo.partes_autoras.add(p)

            # Partes Rés
            res_list = separar_itens_celula(row.get('Partes Rés'))
            for nome_parte in res_list:
                p, _ = Parte.objects.get_or_create(nome=nome_parte)
                processo.partes_res.add(p)

    return f"Sincronização concluída! {len(df)} processos processados."