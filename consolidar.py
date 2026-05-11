import os
import pandas as pd
from pathlib import Path
from django.db import transaction

# Importes ajustados ao seu projeto
from processos.models import (
    Processo, OrgaoJulgador, Classe, 
    MovimentacaoInterna, SituacaoMinuta
)
from processos.services.parser import (
    formatar_numero_processo, 
    limpar_data_excel, 
    obter_ou_criar_responsavel, 
    extrair_autor_obs
)

def run():
    # 1. Configuração do Caminho
    caminho_da_pasta = r"C:\Pendrive\BD\Acervo"
    
    pasta = Path(caminho_da_pasta)
    arquivos = list(pasta.glob("*.xlsx"))
    
    if not arquivos:
        print(f"Erro: Nenhum arquivo .xlsx encontrado em: {caminho_da_pasta}")
        return

    print(f"Lendo {len(arquivos)} arquivos para consolidação...")
    
    lista_df = []
    for arquivo in arquivos:
        dt_mod = os.path.getmtime(arquivo)
        try:
            # Lendo Excel (ajuste se for CSV, mas como mencionou pasta com xlsx, mantive read_excel)
            df_temp = pd.read_excel(arquivo)
            df_temp['temp_dt_mod'] = dt_mod
            lista_df.append(df_temp)
        except Exception as e:
            print(f"Erro ao ler {arquivo.name}: {e}")

    if not lista_df:
        return

    # 2. Consolidação: O arquivo mais recente (maior timestamp) vence
    df_total = pd.concat(lista_df, ignore_index=True)
    df_total = df_total.sort_values(by='temp_dt_mod', ascending=True)
    
    # 'Processo Completo' como chave de unicidade
    df_consolidado = df_total.drop_duplicates(subset='Processo Completo', keep='last')
    
    total_registros = len(df_consolidado)
    print(f"Consolidação concluída. {total_registros} processos únicos para processar.")

    # 3. Importação seguindo o models.py
    stats = {"novos": 0, "atualizados": 0}
    
    with transaction.atomic():
        for index, row in df_consolidado.iterrows():
            try:
                processo_completo = str(row.get('Processo Completo', '')).strip()
                fase, numero = formatar_numero_processo(processo_completo)
                
                processo_existente = Processo.objects.filter(numero=numero).first()

                # Mapeamento corrigido conforme seu models.py e colunas do Acervo
                dados_processo = {
                    'numero': numero,
                    'fase_completa': fase,
                    # No seu model o campo é 'data_entrada' e no Excel a coluna é 'Entrada'
                    'data_entrada': limpar_data_excel(row.get('Entrada')),
                    'responsavel': obter_ou_criar_responsavel(row.get('Responsável')),
                    'orgao_julgador': OrgaoJulgador.objects.get_or_create(
                        nome=str(row.get('Orgão Julgador Colegiado', '')).strip()
                    )[0],
                    'classe': Classe.objects.get_or_create(
                        nome=str(row.get('Classe', '')).strip()
                    )[0],
                    'movimentacao_interna': MovimentacaoInterna.objects.get_or_create(
                        nome=str(row.get('Movimentação Interna', '')).strip()
                    )[0],
                    'situacao_minuta': SituacaoMinuta.objects.get_or_create(
                        nome=str(row.get('Situação Minuta', '')).strip()
                    )[0],
                    'andamento': str(row.get('Andamento', '')).strip()[:255], # Limite do CharField
                    'movimentacoes': str(row.get('Movimentacoes', '')).strip(),
                    'obs': extrair_autor_obs(row.get('Observações'))[1],
                }

                obj, created = Processo.objects.update_or_create(
                    id=processo_existente.id if processo_existente else None,
                    defaults=dados_processo
                )

                if created:
                    stats["novos"] += 1
                else:
                    stats["atualizados"] += 1
                
                if (stats["novos"] + stats["atualizados"]) % 100 == 0:
                    print(f"Progresso: {stats['novos'] + stats['atualizados']}/{total_registros}")

            except Exception as e:
                print(f"Erro no processo {row.get('Processo Completo')}: {e}")

    print(f"\nSucesso! Novos: {stats['novos']} | Atualizados: {stats['atualizados']}")

if __name__ == "__main__":
    run()