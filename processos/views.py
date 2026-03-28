from django.shortcuts import render
from .services.downloader import baixar_planilha_acervo
from .services.importer import processar_arquivo_excel # Vamos criar este

def atualizar_banco(request):
    if request.method == "POST":
        # 1. O robô baixa o arquivo
        caminho_arquivo = baixar_planilha_acervo()
        
        if caminho_arquivo:
            # 2. O importador lê o arquivo e salva no banco
            resultado = processar_arquivo_excel(caminho_arquivo)
            return render(request, 'processos/sucesso.html', {'msg': resultado})
            
    return render(request, 'processos/atualizar.html')