import FreeSimpleGUI as sg
import json
import os
import re
import shutil
import time
import timeit
import traceback
import threading
from django.http import StreamingHttpResponse
from .models import TriagemMPPF, Materia, ExpressaoMateria, ResultadoTriagem, TriagemMateria
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q, Value, Max, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect
from pathlib import Path
from processos.models import Processo, Peca
from .models import TriagemMPPF
from .services.abre_pdf import abre_pdf_do_processo
from .services.corrige_copia_pdf import corrige_texto_pdf
from .services.utils import limpar_texto
from .services.filtros import *
from .services.automatizacao_ge import GEBot


# Relatórios

def kanban_triagem(request):
    print('kanban_triagem', flush=True)
    listas = [
        {
            'nome': 'Disponível',
            'processos': incluir_triagem(),
        },
        {
            'nome': 'Triar',
            'processos': triar().order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'PDF',
            'processos': triar_com_pdf().order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Triados',
            'processos': triados(),
        },
        {
            'nome': 'Não fazer',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='nao-fazer').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Fazer MPPF',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='fazer-mppf').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Fazer MPPF IN40',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='fazer-mppf-in40').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Fazer MPPF Misto',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='fazer-mppf-misto').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Reautuar RR',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='reautuar-como-rr').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Reautuar RRAg',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='reautuar-como-rrag').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Suspender',
            'processos': triados_sem_minuta().filter(triagem_mppf__resultado__slug='suspender').order_by('qtd_recursos', 'id'),
        },
        {
            'nome': 'Criada a minuta',
            'processos': criada_minuta_GE(),
        },
        {
            'nome': 'Lançada DA no GE',
            'processos': lancada_DA_no_GE(),
        },
        {
            'nome': 'Código 235.',
            'processos': codigo_235(),
        },
        {
            'nome': 'Código 239.',
            'processos': codigo_239(),
        },
        {
            'nome': 'Código 242.',
            'processos': codigo_242(),
        },
        {
            'nome': 'Assinatura',
            'processos': enviado_para_assinatura(),
        },
    ]
    contexto = {
        'listas': listas
    }

    return render(request, 'mppf/kanban.html', contexto)


def relatorio_nao_fazer(request):
    print('relatorio_nao_fazer')
    """
    Relatório 1: Processos marcados como 'Não fazer', organizados por matéria.
    """
    # Filtra as triagens que tiveram o resultado "não-fazer"
    triagens_nao_fazer = TriagemMPPF.objects.filter(
        resultado__slug__in=['nao-fazer', 'suspender'],
        processo__classe__nome='AIRR',
        processo__responsavel__nome_completo='Danilo Monteiro De Melo Santos',
        processo__movimentacao_interna__nome='(GE) Triagem Geral',
        processo__esta_no_acervo=True,        
    ).select_related('processo')
    
    # 2. Busca TODAS as matérias, mas APENAS aquelas que estão vinculadas
    # ao queryset restrito que acabamos de criar acima.
    materias = Materia.objects.filter(
        triagens_onde_aparece__in=triagens_nao_fazer
    ).distinct().prefetch_related(
        Prefetch(
            'triagens_onde_aparece', # related_name definido no modelo
            queryset=triagens_nao_fazer, 
            to_attr='triagens_filtradas'
        )
    ).order_by('nome')
    
    # É importante pegar também os processos marcados como "não fazer" 
    # mas que, por algum motivo, não tiveram nenhuma matéria vinculada
    triagens_sem_materia = triagens_nao_fazer.filter(materias__isnull=True)
    print(triagens_nao_fazer.count())
    print(materias.count())

    context = {
        'materias': materias,
        'triagens_sem_materia': triagens_sem_materia,
    }
    
    return render(request, 'mppf/nao_fazer.html', context)


def relatorio_aguardando_triagem(request):
    print('relatorio_aguardando_triagem')
    """
    Relatório 2: Processos aguardando triagem (resultado nulo),
    ordenados decrescentemente pelo tamanho (páginas estimadas).
    """
    # Filtra as triagens sem resultado e ordena pelas maiores (paginas)
    # Coloquei a quantidade de recursos como critério de desempate
    triagens_aguardando = TriagemMPPF.objects.filter(
        resultado__isnull=True
    ).select_related('processo').order_by('-paginas', '-quantidade_de_recursos')
    
    context = {
        'triagens': triagens_aguardando,
        'total_aguardando': triagens_aguardando.count()
    }
    
    return render(request, 'mppf/aguardando_triagem.html', context)


def criar_triagem_MPPF(request):
    print('criar_triagem_MPPF', flush=True)
    """
    Filtra processos AIRR do Danilo em Triagem Geral, cria a ficha TriagemMPPF
    e importa o texto do Despacho de Admissibilidade automaticamente.
    """
    processos = incluir_triagem()
    total = processos.count()

    criados = 0

    for i, processo in enumerate(processos, start=1):
        processo.sincronizar_pecas()
        processo.save()
        triagem, created = TriagemMPPF.objects.get_or_create(
            processo=processo,            
        )
        if created:            
            pecas_da = processo.pecas.filter(
                tipo_peca__nome="Despacho de Admissibilidade do TRT"
            ).order_by('data_publicacao')
            textos_compilados = []            
            for peca in pecas_da:
                if peca.conteudo_texto:
                    cabecalho = f"--- DA (Cód: {peca.cod_peca} - {peca.data_publicacao.strftime('%d/%m/%Y')}) ---"
                    textos_compilados.append(f"{cabecalho}\n{peca.conteudo_texto}")
            texto_da_final = "\n\n".join(textos_compilados)  
            triagem.texto_despacho_admissibilidade = texto_da_final         
            criados += 1
            triagem.save()
        sg.one_line_progress_meter('criar_triagem_MPPF', i, total, orientation='h')

    messages.success(request, f"Fila atualizada: {criados} novas triagens.")
    return redirect('mppf:kanban_triagem')


def proximo_triagem(request):
    pasta = Path(r"D:/Processos")
    pdfs = [arquivo.stem for arquivo in pasta.glob("*.pdf")]
    proximo = TriagemMPPF.objects.get(processo=proximo_triar())

    if proximo:
        # Redireciona para a view de realizar_triagem que criamos antes
        return redirect('mppf:realizar_triagem', pk=proximo.id)
    else:
        # Se não houver nada, volta para o Kanban com um aviso
        messages.info(request, "Não há processos pendentes na fila de triagem!")
        return redirect('mppf:kanban_triagem')


def lancar_fluxo_lote(request):
    if request.method == "POST":
        acao = request.POST.get("acao")
        processos_raw = request.POST.get("processos", "")
        
        # Divide os números colados separando por quebras de linha ou vírgulas, e remove espaços em branco
        lista_numeros = [p.strip() for p in re.split(r'[,\n]+', processos_raw) if p.strip()]
        
        if acao == "minuta_ge":
            # Atualiza todas as triagens vinculadas a processos cujos números estejam na lista
            atualizados = TriagemMPPF.objects.filter(processo__numero__in=lista_numeros).update(foi_criada_minuta_GE=True)
            messages.success(request, f"{atualizados} processos marcados com 'Minuta no GE'.")
            
        elif acao == "assinatura":
            atualizados = TriagemMPPF.objects.filter(processo__numero__in=lista_numeros).update(foi_enviado_para_assinatura=True)
            messages.success(request, f"{atualizados} processos marcados como 'Enviado para assinatura'.")
            
    return redirect('mppf:kanban_triagem')



########################################
# Triagen                              #
########################################
def realizar_triagem(request, pk):    
    largura = shutil.get_terminal_size().columns
    triagem = get_object_or_404(TriagemMPPF, id=pk)
    processo = triagem.processo
    print(f" {processo.fase_completa} - {processo.numero} ".center(largura, "#"))
    print('realizar_triagem')
    
    abre_pdf_do_processo(processo=processo, pasta_processos='D://Processos')
    triagem.texto_despacho_admissibilidade = corrige_texto_pdf(texto=triagem.texto_despacho_admissibilidade)
    triagem.atualizar_paginas()
    if triagem.quantidade_de_recursos is None:
        triagem.quantidade_de_recursos = triagem.processo.partes_autoras.count()
    triagem.save()
    # messages.success(request, f"quantidade_de_recursos_calculada: {triagem.quantidade_de_recursos_calculada}.")

    if request.method == "POST":
        form_name = request.POST.get("form_name")

        if form_name == "editar_DA":
            print(form_name)
            texto = request.POST.get("texto_da")
            texto_limpo = limpar_texto(texto)
            triagem.texto_despacho_admissibilidade = corrige_texto_pdf(texto=texto_limpo)
            triagem.quantidade_de_recursos = int(request.POST.get("quantidade_de_recursos", 1))
            triagem.foi_editada_DA = True
            triagem.conferir_materias_no_texto()                            
            if triagem.quantidade_de_recursos == triagem.quantidade_de_recursos_calculada:
                triagem.foi_conferida_a_quantidade_de_recursos = True
            triagem.save()
            messages.success(request, "Texto e matérias atualizados!")

        elif form_name == "decisao_final":
            acao = request.POST.get("acao") # Recebe 'fazer', 'fazer_in40', etc.
            
            # Busca o objeto de resultado correspondente ao slug enviado
            resultado_obj = ResultadoTriagem.objects.filter(slug=acao, ativo=True).first()
            
            if resultado_obj:
                triagem.resultado = resultado_obj
                triagem.foi_triado = True
                triagem.save()
            
            return redirect('mppf:proximo_triagem')
        
        elif form_name == "remover_materia":
            materia_id = request.POST.get("materia_id")
            if materia_id:
                # Removemos a entrada da tabela intermediária diretamente
                TriagemMateria.objects.filter(triagem=triagem, materia_id=materia_id).delete()
            return redirect('mppf:realizar_triagem', pk=triagem.id)
        
        elif form_name == "adicionar_materia":
            materia_id = request.POST.get("materia_id") # Define a variável primeiro!
            if materia_id:
                materia_nova = get_object_or_404(Materia, id=materia_id)
                # Cria a ligação na tabela intermediária como HUMANO
                TriagemMateria.objects.get_or_create(
                    triagem=triagem,
                    materia=materia_nova,
                    defaults={'origem': TriagemMateria.Origem.HUMANO}
                )
            return redirect('mppf:realizar_triagem', pk=triagem.id)
        
        elif form_name == "adicionar_expressao":
            print(form_name)
            materia_id = request.POST.get("materia_id")
            nova_expressao = request.POST.get("nova_expressao")
            usar_regex = request.POST.get("usar_regex") == "on" # Checkbox retorna 'on' se marcado
            if materia_id and nova_expressao:
                materia = get_object_or_404(Materia, id=materia_id)
                # Cria a nova expressão vinculada à matéria
                ExpressaoMateria.objects.create(
                    materia=materia,
                    texto=nova_expressao,
                    usar_regex=usar_regex
                )
                messages.success(request, f"Expressão adicionada com sucesso à matéria: {materia.nome}")
            return redirect('mppf:realizar_triagem', pk=triagem.id)

        elif form_name == "criar_materia_no_banco":
            print(form_name)
            print(request.POST)
            nome = request.POST.get("nome")
            efeito = request.POST.get("efeito")
            
            if nome and efeito:
                # Cria a matéria no banco (ou recupera se já existir com esse nome)
                materia, created = Materia.objects.get_or_create(
                    nome=nome, 
                    defaults={'efeito': efeito}
                )
                
                # Vincula automaticamente à triagem atual
                triagem.materias.add(materia)
                
                if created:
                    messages.success(request, f"Matéria '{nome}' criada e adicionada a este processo.")
                else:
                    messages.success(request, f"A matéria '{nome}' já existia e foi vinculada a este processo.")
            
            return redirect('mppf:realizar_triagem', pk=triagem.id)
        
        elif form_name == "atualizar_pecas":
            # 1. Executa a função de sincronização no objeto processo
            processo.sincronizar_pecas() 
            # print(triagem.foi_editada_DA)
            if not triagem.foi_editada_DA:
                pecas_da = processo.pecas.filter(
                    tipo_peca__nome="Despacho de Admissibilidade do TRT"
                ).order_by('data_publicacao')
                print(f"Qte peças: {pecas_da.count()}")
                textos_compilados = []
                for peca in pecas_da:
                    if not peca.conteudo_texto:
                        peca.baixar_texto()
                    print(peca.conteudo_texto)
                    cabecalho = f"--- DA (Cód: {peca.cod_peca} - {peca.data_publicacao.strftime('%d/%m/%Y')}) ---"
                    textos_compilados.append(f"{cabecalho}\n{peca.conteudo_texto}")
                
                # 3. Atualiza o texto da triagem e executa a conferência automática
                triagem.texto_despacho_admissibilidade = "\n---\n".join(textos_compilados)
                
                # 4. Aplica correções e guarda
                triagem.texto_despacho_admissibilidade = corrige_texto_pdf(texto=triagem.texto_despacho_admissibilidade)
                triagem.conferir_materias_no_texto()
            
            messages.success(request, "Peças sincronizadas e texto atualizado com sucesso!")
            return redirect('mppf:realizar_triagem', pk=triagem.id)
        
        elif form_name == "atualizar_materias":
            triagem.conferir_materias_no_texto()
            messages.success(request, "Varredura de matérias concluída com sucesso!")
            return redirect('mppf:realizar_triagem', pk=triagem.id)

        elif form_name == "baixar_DA":
            # 1. Tenta sincronizar peças se não há nenhuma DA ainda
            if not processo.pecas.filter(tipo_peca__sigla="DA").exists():
                processo.sincronizar_pecas()

            # 2. Baixa as DAs que ainda não têm texto
            pecas_pendentes = processo.pecas.filter(tipo_peca__sigla="DA", conteudo_texto__isnull=True)
            baixadas = 0
            for peca in pecas_pendentes:
                sucesso, _ = peca.baixar_texto()
                if sucesso:
                    baixadas += 1

            # 3. Popula texto_despacho_admissibilidade com todas as DAs que têm conteúdo
            pecas_com_texto = processo.pecas.filter(
                tipo_peca__sigla="DA", conteudo_texto__isnull=False
            ).order_by('data_publicacao')

            if pecas_com_texto.exists():
                textos = []
                for peca in pecas_com_texto:
                    cabecalho = f"--- DA (Cód: {peca.cod_peca} - {peca.data_publicacao.strftime('%d/%m/%Y')}) ---"
                    textos.append(f"{cabecalho}\n{peca.conteudo_texto}")
                triagem.texto_despacho_admissibilidade = corrige_texto_pdf(
                    texto="\n\n".join(textos)
                )
                triagem.atualizar_paginas()
                triagem.conferir_materias_no_texto()
                triagem.save()
                suffix = f" ({baixadas} baixada(s) agora)" if baixadas else " (texto já estava no banco)"
                messages.success(request, f"Texto da DA atualizado.{suffix}")
            else:
                messages.warning(request, "Nenhuma DA com texto encontrada. Verifique se as peças estão sincronizadas.")
            return redirect('mppf:realizar_triagem', pk=triagem.id)

        return redirect('mppf:realizar_triagem', pk=triagem.id)

    # --- LÓGICA DE GET (Renderização da Página) ---
    todas_materias = Materia.objects.filter(ativa=True)
    
    # 1. Preparar o texto para exibição com destaques (Highlight)
    texto_raw = triagem.texto_despacho_admissibilidade or ""
    texto_formatado = texto_raw

    # Pega apenas as expressões das matérias que já foram identificadas neste processo
    expressoes_encontradas = ExpressaoMateria.objects.filter(materia__in=triagem.materias.all())

    for exp in expressoes_encontradas:
        if exp.usar_regex:
            pattern = re.compile(exp.texto, re.IGNORECASE)
        else:
            # Escapa o texto para não quebrar a regex
            pattern = re.compile(re.escape(exp.texto), re.IGNORECASE)
            
        # Substitui a ocorrência por uma tag <mark> do Bootstrap
        texto_formatado = pattern.sub(lambda m: f"<mark class='text-warning-emphasis rounded px-1'>{m.group(0)}</mark>", texto_formatado)

    # Converte as quebras de linha padrão para tags <br> para o HTML renderizar corretamente
    linhas_formatadas = texto_formatado.split('\n')
    
    # Pega as matérias que já estão na triagem
    materias_vinculadas = triagem.materias.all()

    # Busca as matérias que NÃO estão nesta triagem e aplica a ordenação personalizada
    materias_disponiveis = Materia.objects.filter(ativa=True).exclude(
            id__in=materias_vinculadas
        ).annotate(
            maior_prioridade=Coalesce(Max('solucoes_compativeis__nivel_prioridade'), Value(0))
        ).order_by('-maior_prioridade', 'nome')

    # --- LÓGICA DE STATS ---
    feitos = produtividade_feitos().count()
    total = produtividade_geral().count()
    aproveitados = produtividade_aproveitados().count()
    feitos_acervo = produtividade_feitos_acervo().count()
    total_acervo= produtividade_geral_acervo().count()
    aproveitados_acervo = produtividade_aproveitados_acervo().count()
    
    context = {
        'triagem': triagem,
        'solucoes_permitidas': triagem.get_solucoes_permitidas(),
        'todas_solucoes': ResultadoTriagem.objects.filter(ativo=True),
        'processo': processo,
        'materias_disponiveis': materias_disponiveis,
        'linhas_formatadas': linhas_formatadas,
        'texto_raw': texto_raw,
        # Stats
        'feitos': feitos,
        'total': total,
        'faltam': total - feitos,
        'percentual_concluido': round(feitos / total * 100, 1),
        'aproveitados': aproveitados,
        'percentual_aproveitados': round(aproveitados / feitos * 100, 1),
        'feitos_acervo': feitos_acervo,
        'total_acervo': total_acervo,
        'faltam_acervo': total_acervo - feitos_acervo,
        'percentual_concluido_acervo': round(feitos_acervo / total_acervo * 100, 1),
        'aproveitados_acervo': aproveitados_acervo,
        'percentual_aproveitados_acervo': round(aproveitados_acervo / feitos_acervo * 100, 1),
    }
    
    return render(request, 'mppf/triagem.html', context)


def lanca_DA_no_GE_semiauto(request):
    from .services.progresso import iniciar, esta_rodando

    if esta_rodando():
        return redirect('mppf:progresso_ge')

    processos = list(
        criada_minuta_GE().select_related('classe', 'triagem_mppf')
    )
    iniciar()
    threading.Thread(
        target=_rodar_automacao_ge,
        args=(processos,),
        daemon=True,
    ).start()
    return redirect('mppf:progresso_ge')


def _rodar_automacao_ge(processos):
    import pythoncom
    from .services.progresso import push, finalizar

    # COM (win32com/Word) exige inicialização explícita em threads não-principais
    pythoncom.CoInitialize()

    total = len(processos)
    push({'tipo': 'inicio', 'total': total})

    def _log_sse(msg, sucesso=None):
        push({'tipo': 'log', 'mensagem': msg, 'sucesso': sucesso})

    gebot = GEBot(log_fn=_log_sse)
    try:
        gebot.login()
    except Exception as e:
        push({'tipo': 'log', 'mensagem': f'ERRO no login: {e}', 'sucesso': False})
        finalizar()
        return

    push({'tipo': 'log', 'mensagem': 'Escaninho pronto. Iniciando consultas...', 'sucesso': True})
    inicio = time.monotonic()
    exclusao = gebot.lista_exclusao()
    print(exclusao)
    print(total)

    for i, processo in enumerate(processos, start=1):
        elapsed = time.monotonic() - inicio
        eta = (elapsed / i) * (total - i) if i > 1 else 0
        push({
            'tipo': 'progresso',
            'atual': i,
            'total': total,
            'processo': f'{processo.classe} - {processo.numero}',
            'elapsed': elapsed,
            'eta': eta,
        })
        print(f"Iniciando: {processo.classe} - {processo.numero}")

        if processo.numero in exclusao:
            push({'tipo': 'log', 'mensagem': f'Pulado (exclusão): {processo.numero}'})
            continue

        try:
            gebot.seleciona_processo(numero=processo.numero)
            sucesso = gebot.lanca_DA(processo=processo)
            if sucesso:
                push({'tipo': 'log', 'mensagem': f'DA lançada: {processo.numero}', 'sucesso': True})
            else:
                push({'tipo': 'log', 'mensagem': f'Falhou (DA não inserida): {processo.numero}', 'sucesso': False})

        except Exception as e:
            print(f"ERRO ao processar {processo.numero}: {e}")
            traceback.print_exc()
            push({'tipo': 'log', 'mensagem': f'ERRO: {processo.numero} — {e}', 'sucesso': False})
            try:
                gebot.driver.get(gebot.URL_GERENCIAL)
            except Exception as recovery_error:
                print(f"Falha ao recuperar estado: {recovery_error}")

    push({'tipo': 'fim', 'total': total})
    finalizar()
    pythoncom.CoUninitialize()


def progresso_ge(request):
    return render(request, 'mppf/progresso_ge.html')


def progresso_ge_pronto(request):
    from .services.progresso import sinalizar_gerencial_pronto
    from django.http import JsonResponse
    sinalizar_gerencial_pronto()
    return JsonResponse({'ok': True})


def progresso_ge_stream(request):
    from .services.progresso import get_fila

    def stream():
        fila = get_fila()
        while True:
            try:
                evento = fila.get(timeout=25)
                if evento is None:
                    yield f'data: {json.dumps({"tipo": "fim", "total": 0})}\n\n'
                    break
                yield f'data: {json.dumps(evento)}\n\n'
            except Exception:
                yield ': keepalive\n\n'

    response = StreamingHttpResponse(stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response