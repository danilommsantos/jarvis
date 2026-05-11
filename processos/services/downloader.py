import os
import time
import glob
from datetime import datetime
# Importações do Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

def baixar_planilha_acervo():
    print("baixar_planilha_acervo")
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
    wait = WebDriverWait(driver, 30) # Espera até 30 segundos pelos elementos
    
    try:
        # Pega a lista de arquivos antes para saber qual é o novo
        arquivos_antes = set(glob.glob(os.path.join(pasta_downloads, "*.xlsx")))
        # Acessar o site
        driver.get("https://bemtevi.tst.jus.br")
        
        # --- AQUI VAI O SEU CÓDIGO DE LOGIN E NAVEGAÇÃO DO BOTS.PY ---
        # =========================================================
        # PASSO 1: LOGIN (Você pode precisar ajustar os XPaths aqui)
        # =========================================================
        cpf = os.getenv('CPF')
        senha = os.getenv('PASS')
        
        if not cpf or not senha:
            raise ValueError("As variáveis de ambiente CPF e PASS não estão configuradas no .env!")

        # Aguarda o campo de CPF aparecer (tenta achar um input de texto padrão de login)
        # OBS: Se o BemTeVi usar IDs específicos como id="username", mude aqui:
        campo_cpf = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text' or contains(@name, 'cpf') or contains(@id, 'cpf') or contains(@id, 'username')]")))
        campo_cpf.send_keys(cpf)
        
        campo_senha = driver.find_element(By.XPATH, "//input[@type='password']")
        campo_senha.send_keys(senha)
        
        # Em vez de procurar o botão e clicar, damos apenas um ENTER!
        campo_senha.send_keys(Keys.RETURN)
        
        # =========================================================
        # PASSO 2: NAVEGAÇÃO
        # =========================================================
        # Clicar na Ministra
        ministra = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Ministra Kátia Magalhães Arruda')]")))
        ministra.click()
        
        # ---------------------------------------------------------
        # A MAGIA ESTÁ AQUI: Esperar a tela de carregamento sumir!
        # ---------------------------------------------------------
        time.sleep(1) # Dá 1 segundo para o "backdrop" aparecer na tela
        # O robô vai travar nesta linha e só avança quando o carregamento (backdrop) sumir completamente:
        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        time.sleep(1) # Um respiro extra após a tabela carregar
        
        # Agora que a tabela carregou, clicamos no input gigante
        checkbox = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div[2]/div[2]/div[2]/div[2]/div[2]/div[1]/div/div[1]/div/div/div/span/div/div[1]/input')))
        driver.execute_script("arguments[0].click();", checkbox)
        
        # Clicar em Exportar
        time.sleep(1) 
        btn_exportar = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'exportar')]")))
        driver.execute_script("arguments[0].click();", btn_exportar)
        
        # =========================================================
        # CLIQUE NO EXCEL (ATUALIZADO)
        # =========================================================
        # Esperar a animação do menu abrir completamente
        time.sleep(2) 
        
        # O XPath agora procura exatamente o item de lista (li) que o Material-UI gerou
        xpath_excel = "//li[@role='menuitem' and contains(text(), 'Excel')]"
        btn_excel = wait.until(EC.presence_of_element_located((By.XPATH, xpath_excel)))
        
        try:
            # Tenta dar um clique nativo do rato (o que o React prefere quando o aria-disabled é false)
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_excel))).click()
        except Exception:
            # Se ainda assim houver algo na frente, força com JavaScript
            driver.execute_script("arguments[0].click();", btn_excel)
            
        # =========================================================
        # PASSO 3: ESPERAR O DOWNLOAD TERMINAR E RENOMEAR
        # =========================================================
        # Pega a lista de arquivos Excel na pasta antes do download
        arquivos_antes = set(glob.glob(os.path.join(pasta_downloads, "*.xlsx")))
        
        # Espera até que um novo arquivo .xlsx seja completamente baixado
        # (O Chrome cria um arquivo .crdownload enquanto está baixando)
        tempo_limite = 60
        arquivo_baixado = None
        
        for _ in range(tempo_limite):
            time.sleep(1) # Aguarda 1 segundo
            arquivos_agora = set(glob.glob(os.path.join(pasta_downloads, "*.xlsx")))
            novos_arquivos = arquivos_agora - arquivos_antes
            
            if novos_arquivos:
                # Pegou um arquivo novo!
                arquivo_temp = list(novos_arquivos)[0]
                
                # Checa se não é o download temporário do Chrome
                if not arquivo_temp.endswith('.crdownload'):
                    arquivo_baixado = arquivo_temp
                    break
                    
        if not arquivo_baixado:
            raise Exception("O tempo limite para download expirou (60s).")

        # Renomeia com o padrão desejado
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        novo_caminho = os.path.join(pasta_downloads, f"Acervo_{timestamp}.xlsx")
        
        os.rename(arquivo_baixado, novo_caminho)
        return novo_caminho
            
    finally:
        driver.quit()
    
    return None