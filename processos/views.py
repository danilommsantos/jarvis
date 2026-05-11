from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .services.downloader import baixar_planilha_acervo
from .services.importer import processar_atualizacao_acervo
from .models import Processo, Peca
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
    processos = Processo.objects.filter(esta_no_acervo=True)
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


def baixar_texto_DA_AIRRs(request):
    # 1. Procura o processo
    processos = Processo.objects.filter(
        classe__nome="AIRR", 
        esta_no_acervo=True,
        responsavel__nome_completo = "Danilo Monteiro De Melo Santos",
        )
    total = processos.count()    
    for i, processo in enumerate(processos, start=1):
        ic(processo.numero)
        pecas = processo.pecas.filter(tipo_peca__sigla="DA", conteudo_texto__isnull=False)
        ic(pecas.count())
        for peca in pecas:
            peca.baixar_texto()
            peca.save()
        sg.one_line_progress_meter('baixar_texto_DA_AIRRs', i, total, orientation='h')
    messages.success(request, f"Sucesso: foram atualizados {total} processos.")
    return redirect('lista_processos')