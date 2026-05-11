import pandas as pd
import FreeSimpleGUI as sg
from django.db import transaction
from django.contrib.auth.models import User
from ..models import (
    Processo, Advogado, Parte, OrgaoJulgador, 
    TipoMinuta, SituacaoMinuta, MovimentacaoInterna, 
    Classe, Assunto, Responsavel
)
from .parser import *


def processar_atualizacao_acervo(caminho_arquivo):
    print("processar_atualizacao_acervo")
    df = pd.read_excel(caminho_arquivo)
    stats = {"novos": 0, "atualizados": 0, "corrigidos": 0}

    with transaction.atomic():
        Processo.objects.all().update(esta_no_acervo=False)
        ids_processados_no_excel = []
        total = len(df.index)
        for i, row in df.iterrows():
            sg.one_line_progress_meter('Atualiza acervo', i, total, orientation='h')
            texto_bruto = str(row.get('Processo Completo', '')).strip()
            fase_extraida, num_formatado = formatar_numero_processo(texto_bruto)
            
            # Tenta localizar o processo por 3 vias:
            # 1. Pelo número formatado (Ideal)
            # 2. Pelo texto bruto (Caso tenha dado erro de formato antes)
            processo_existente = Processo.objects.filter(numero=num_formatado).first()
            if not processo_existente:
                processo_existente = Processo.objects.filter(numero=texto_bruto).first()

            # Preparamos os dados para atualizar/criar
            dados_processo = {
                'numero': num_formatado,
                'fase_completa': fase_extraida,
                'data_entrada': limpar_data_excel(row.get('Entrada')),
                'responsavel': obter_ou_criar_responsavel(row.get('Responsável')),
                'orgao_julgador': OrgaoJulgador.objects.get_or_create(nome=str(row.get('Orgão Julgador Colegiado', '')).strip())[0],
                'classe': Classe.objects.get_or_create(nome=str(row.get('Classe', '')).strip())[0],
                'movimentacao_interna': MovimentacaoInterna.objects.get_or_create(nome=str(row.get('Movimentação Interna', '')).strip())[0],
                'situacao_minuta': SituacaoMinuta.objects.get_or_create(nome=str(row.get('Situação Minuta', '')).strip())[0],
                'andamento': str(row.get('Andamento', '')).strip(),
                'movimentacoes': str(row.get('Movimentações', '')).strip(),
                'obs': extrair_autor_obs(row.get('Observações'))[1],
                'esta_no_acervo': True,
            }

            # Executa a mágica: 
            # Se achou pelo ID, ele dá UPDATE em tudo que está nos dados_processo.
            # Se não achou, ele dá INSERT.
            obj, created = Processo.objects.update_or_create(
                id=processo_existente.id if processo_existente else None,
                defaults=dados_processo
            )
        
            # --- LÓGICA DE RELACIONAMENTOS (M2M) ---       
            def vincular_items(coluna, model_classe, campo_m2m):
                """Auxiliar para processar strings multilinhas e vincular ao processo"""
                conteudo = str(row.get(coluna, ''))
                if conteudo and conteudo.lower() != 'nan':
                    # Divide por quebra de linha e remove espaços vazios
                    nomes = [n.strip() for n in conteudo.split('\n') if n.strip()]
                    objs = []
                    for nome in nomes:
                        # No caso de Parte, Advogado e Assunto, o campo é 'nome'
                        item_obj, _ = model_classe.objects.get_or_create(nome=nome)
                        objs.append(item_obj)
                    
                    # Usa .set() para substituir os vínculos antigos pelos novos
                    getattr(obj, campo_m2m).set(objs)

            # 1. Partes (Ajuste o nome da coluna do Excel se necessário)
            vincular_items('Partes Autoras', Parte, 'partes_autoras')
            vincular_items('Partes Rés', Parte, 'partes_res')
            # 2. Advogados
            vincular_items('Advogados', Advogado, 'advogados')
            # 3. Assuntos
            vincular_items('Assuntos', Assunto, 'assuntos')

            # Contabiliza para o relatório final
            if created:
                stats["novos"] += 1
            else:
                if processo_existente.fase_completa == 'ERRO_FORMATO' and obj.fase_completa != 'ERRO_FORMATO':
                    stats["corrigidos"] += 1
                stats["atualizados"] += 1

    return f"J.A.R.V.I.S. sincronizado: {stats['novos']} novos, {stats['atualizados']} atualizados ({stats['corrigidos']} correções de erro)."