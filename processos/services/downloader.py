import os
import time
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# ... (outras importações de Selenium que você já tem no bots.py)

def baixar_planilha_acervo():
    """
    Executa o bot Selenium para baixar o arquivo.
    Retorna o caminho completo do arquivo baixado.
    """
    # Usando o caminho que você já definiu no seu código original
    pasta_downloads = r'C:\Pendrive\BD\Acervo'
    
    if not os.path.exists(pasta_downloads):
        os.makedirs(pasta_downloads)

    chrome_options = Options()
    # Descomente a linha abaixo se quiser que o robô trabalhe escondido
    # chrome_options.add_argument("--headless") 
    
    prefs = {
        "download.default_directory": pasta_downloads,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Pega a lista de arquivos antes para saber qual é o novo
        arquivos_antes = set(glob.glob(os.path.join(pasta_downloads, "*.xlsx")))
        
        # --- AQUI VAI O SEU CÓDIGO DE LOGIN E NAVEGAÇÃO DO BOTS.PY ---
        driver.get("URL_DO_SISTEMA") 
        # ... (seu código de clicar, logar e baixar)
        
        # Espera o download (seu laço de 60 segundos do bots.py)
        arquivo_baixado = None
        for _ in range(60):
            time.sleep(1)
            arquivos_agora = set(glob.glob(os.path.join(pasta_downloads, "*.xlsx")))
            novos = arquivos_agora - arquivos_antes
            if novos:
                temp = list(novos)[0]
                if not temp.endswith('.crdownload'):
                    arquivo_baixado = temp
                    break
        
        if arquivo_baixado:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            novo_caminho = os.path.join(pasta_downloads, f"Acervo_{timestamp}.xlsx")
            os.rename(arquivo_baixado, novo_caminho)
            return novo_caminho
            
    finally:
        driver.quit()
    
    return None