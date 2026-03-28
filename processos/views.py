from django.shortcuts import render, redirect
from django.contrib import messages
from .services.downloader import baixar_planilha_acervo
from .services.importer import processar_atualizacao_acervo
from .models import Processo

def dashboard_processos(request):
    # Mostra os últimos 10 processos importados apenas para conferência
    recentes = Processo.objects.all().order_index('-id')[:10]
    return render(request, 'processos/dashboard.html', {'recentes': recentes})

def disparar_atualizacao(request):
    if request.method == "POST":
        try:
            # 1. Chama o Selenium (do seu bots.py)
            caminho_arquivo = baixar_planilha_acervo()
            
            if caminho_arquivo:
                # 2. Chama o Importador (que usa o parser)
                processar_atualizacao_acervo(caminho_arquivo)
                messages.success(request, "Base de dados atualizada com sucesso!")
            else:
                messages.error(request, "Falha ao baixar o arquivo do sistema.")
                
        except Exception as e:
            messages.error(request, f"Erro durante a atualização: {e}")
            
        return redirect('dashboard_processos')