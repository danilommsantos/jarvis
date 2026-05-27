from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .services.downloader import baixar_planilha_acervo
from .services.importer import processar_atualizacao_acervo
from .models import Processo, Peca
from mppf.services.corrige_copia_pdf import corrige_texto_pdf
import FreeSimpleGUI as sg
from icecream import ic


def dashboard(request):
    # Mostra os últimos 10 processos importados apenas para conferência
    recentes = Processo.objects.all().order_index('-id')[:10]
    return render(request, 'processos/dashboard.html', {'recentes': recentes})


def atualizar_acervo(request):
    try:
        # PASSO 1: O robô entra em ação e baixa o arquivo
        messages.info(request, "J.A.R.V.I.S. acessando o tribunal... Aguarde.")
        caminho_excel = baixar_planilha_acervo() # Seu script do Selenium
        
        # PASSO 2: O importador lê o arquivo baixado e salva no banco
        resultado = processar_atualizacao_acervo(caminho_excel)
        
        messages.success(request, f"Sucesso: {resultado}")
        
    except Exception as e:
        messages.error(request, f"Falha na automação: {str(e)}")
    return redirect('lista_processos')
    

def lista_processos(request):
    processos = Processo.objects.select_related('responsavel', 'orgao_julgador').all().order_by('-data_entrada')    
    return render(request, 'processos/lista.html', {'processos': processos})


def atualizar_json_processos(request):
    tudo = request.GET.get('tudo') == '1'
    processos = Processo.objects.filter(esta_no_acervo=True)
    if not tudo:
        # apenas processos que ainda não têm peças sincronizadas
        processos = processos.filter(pecas__isnull=True)
    total = processos.count()
    for i, processo in enumerate(processos, start=1):
        sucesso, mensagem = processo.sincronizar_pecas()
        print(mensagem)
        sg.one_line_progress_meter('Atualiza peças json', i, total, orientation='h')
    messages.success(request, f"Sucesso: foram atualizados {total} processos.")
    return redirect('lista_processos')


def sincronizar_processo(request, pk):
    # 1. Procura o processo
    processo = get_object_or_404(Processo, pk=pk)    
    # 2. Chama o método que criámos no modelo
    sucesso, mensagem = processo.sincronizar_pecas()    
    # 3. Exibe a mensagem no sistema do Django
    if sucesso:
        messages.success(request, mensagem)
    else:
        messages.error(request, mensagem)    
    # 4. Redireciona para onde o utilizador estava (ou para a lista de processos)
    return redirect(request.META.get('HTTP_REFERER', '/admin/processos/processo/'))


def baixar_texto(request, pk):
    # 1. Procura o processo
    peca = get_object_or_404(Peca, pk=pk)
    
    # 2. Chama o método que criámos no modelo
    sucesso, mensagem = peca.baixar_texto()
    
    # 3. Exibe a mensagem no sistema do Django
    if sucesso:
        messages.success(request, mensagem)
    else:
        messages.error(request, mensagem)
    
    # 4. Redireciona para onde o utilizador estava (ou para a lista de processos)
    return redirect(request.META.get('HTTP_REFERER', '/admin/processos/peca/'))


def processo_detalhe(request, pk):
    processo = get_object_or_404(
        Processo.objects.select_related(
            'responsavel', 'relator', 'orgao_julgador', 'classe',
            'movimentacao_interna', 'tipo_minuta', 'situacao_minuta',
            'obs_responsavel',
        ).prefetch_related(
            'partes_autoras', 'partes_res', 'advogados', 'assuntos',
            'pecas__tipo_peca',
        ),
        pk=pk,
    )

    try:
        triagem = processo.triagem_mppf
    except Exception:
        triagem = None

    revisoes = (
        processo.revisoes_pauta
        .select_related('pauta', 'minutante')
        .prefetch_related('status')
        .order_by('-pauta__data_inicio')
    )
    memoriais = processo.memoriais.select_related('pauta').all()
    atendimentos = processo.atendimentos.select_related('pauta').order_by('-data_horario')

    return render(request, 'processos/processo_detalhe.html', {
        'processo': processo,
        'triagem': triagem,
        'revisoes': revisoes,
        'memoriais': memoriais,
        'atendimentos': atendimentos,
    })


def baixar_texto_DA_AIRRs(request):
    tudo = request.GET.get('tudo') == '1'
    processos = Processo.objects.filter(
        classe__nome="AIRR",
        esta_no_acervo=True,
        responsavel__nome_completo="Danilo Monteiro De Melo Santos",
    )
    total = processos.count()
    for i, processo in enumerate(processos, start=1):
        ic(processo.numero)

        # Se não tem peças, tenta sincronizar o JSON antes de baixar a DA
        if not processo.pecas.exists():
            ic('JSON não encontrado, sincronizando peças...')
            processo.sincronizar_pecas()

        if tudo:
            pecas = processo.pecas.filter(tipo_peca__sigla="DA")
        else:
            # apenas DAs que ainda não tiveram o texto baixado
            pecas = processo.pecas.filter(tipo_peca__sigla="DA", conteudo_texto__isnull=True)

        ic(pecas.count())
        for peca in pecas:
            peca.baixar_texto()
            peca.save()

        # Popula texto_despacho_admissibilidade somente se ainda estiver vazio
        try:
            triagem = processo.triagem_mppf
            if not triagem.texto_despacho_admissibilidade:
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
                    triagem.save()
        except Exception:
            pass  # Processo sem triagem MPPF — ignora

        sg.one_line_progress_meter('baixar_texto_DA_AIRRs', i, total, orientation='h')
    messages.success(request, f"Sucesso: foram atualizados {total} processos.")
    return redirect('lista_processos')