import os
import time
import pyautogui
import pygetwindow as gw
from PIL import ImageGrab
from django.conf import settings

def localizar_na_tela(caminho_imagem):
    """
    Função auxiliar que tira o print de múltiplos monitores
    e devolve a posição do botão, ignorando erros menores.
    """
    try:
        tela = ImageGrab.grab(all_screens=True)
        return pyautogui.locate(caminho_imagem, tela, confidence=0.8, grayscale=True)
    except Exception as e:
        return None

def clicar_com_retry(img_alvo, desc_alvo, img_confirmacao=None, desc_confirmacao=None, acao_extra=None, timeout=1, max_tentativas=5):
    """
    1. Encontra e clica na imagem alvo.
    2. Opcional: Executa uma ação extra (como colar texto).
    3. Opcional: Aguarda a 'imagem_confirmacao' aparecer por X segundos.
    4. Se a confirmação não aparecer, tenta o processo todo de novo (até max_tentativas).
    """
    for tentativa in range(1, max_tentativas + 1):
        print(f"\n--- [Tentativa {tentativa}/{max_tentativas}] Clicando em '{desc_alvo}' ---")
        
        # PASSO 1: Encontrar e clicar no botão alvo
        start_busca = time.time()
        clicou = False
        
        # Tenta achar o botão de clique por até 5 segundos
        while time.time() - start_busca < 5:
            pos_alvo = localizar_na_tela(img_alvo)
            if pos_alvo:
                centro_x, centro_y = pyautogui.center(pos_alvo)
                pyautogui.click(centro_x, centro_y)
                print(f" > Clique efetuado no botão '{desc_alvo}'.")
                clicou = True
                break
            time.sleep(0.5)
            
        if not clicou:
            print(f" X Botão '{desc_alvo}' não encontrado. Tentando novamente...")
            continue # Pula para a próxima rodada do loop for
            
        # PASSO 2: Ação extra opcional (ex: Colar número e dar Enter)
        if acao_extra:
            time.sleep(0.5) # Pausa rápida para o clique fazer efeito
            acao_extra()
            
        # PASSO 3: Se não tem imagem para confirmar, consideramos um sucesso
        if not img_confirmacao:
            return True
            
        # PASSO 4: Aguardar a imagem de confirmação (a próxima tela)
        print(f" > Aguardando '{desc_confirmacao}' (Timeout de {timeout}s)...")
        start_espera = time.time()
        confirmado = False
        
        while time.time() - start_espera < timeout:
            pos_confirma = localizar_na_tela(img_confirmacao)
            if pos_confirma:
                print(f" V Imagem de referência '{desc_confirmacao}' confirmada!")
                confirmado = True
                break
            time.sleep(0.5)
            
        if confirmado:
            return True # O fluxo deu 100% certo! Sai da função.
        else:
            print(f" X Timeout: '{desc_confirmacao}' não apareceu. Repetindo clique inicial...")
            # O loop for vai girar e tentar clicar no botão original mais uma vez
            
    print(f"!!! Falha Crítica: Esgotadas as {max_tentativas} tentativas para a ação '{desc_alvo}'.")
    return False


def abre_voto_ge(numero_processo):
    """Executa a rotina de cliques na janela do Vivaldi."""
    if any(numero_processo in w.title for w in gw.getWindowsWithTitle('Word')):
        print(f"Automação abortada: Word já aberto para o processo {numero_processo}")
        return False

    try:
        vivaldi_windows = gw.getWindowsWithTitle('Vivaldi')
        if not vivaldi_windows:
            print("Nenhuma janela do Vivaldi encontrada.")
            return False
        
        target_web = vivaldi_windows[0]
        if target_web.isMinimized:
            target_web.restore()
        target_web.activate()
        time.sleep(1)

        # Ajuste de caminho baseado no seu print da tela
        base_path = os.path.join(settings.BASE_DIR, 'pautas', 'services', 'assets')
        
        img_consulta = os.path.join(base_path, "consulta_btn.png")
        img_editar = os.path.join(base_path, "editar_voto_btn.png")
        img_word = os.path.join(base_path, "abrir_word_btn.png")

        if not os.path.exists(img_consulta):
            print(f"ERRO: Imagem não encontrada no caminho -> {img_consulta}")
            return False

        # --- AÇÕES DA AUTOMAÇÃO ---
        
        # Função para ser injetada e chamada logo após clicar em "Consulta"
        def acao_colar_e_buscar():
            pyautogui.hotkey('ctrl', 'v')
            for _ in range(8):
                pyautogui.press('tab')    
            pyautogui.press('enter')

        # 1. Clicar em Consulta -> Colar Número -> Confirmar que "Editar Voto" apareceu
        sucesso_consulta = clicar_com_retry(
            img_alvo=img_consulta,
            desc_alvo="Consulta Processo",
            img_confirmacao=img_editar,
            desc_confirmacao="Editar Voto",
            acao_extra=acao_colar_e_buscar, # Passamos a função de colar/enter para ele executar
            timeout=10,
            max_tentativas=10
        )
        

        # Se após 10 tentativas de 10s não passou, cancela a operação
        if not sucesso_consulta: 
            return False 

        # 2. Clicar em Editar Voto -> Confirmar que "Abrir Word" apareceu
        sucesso_editar = clicar_com_retry(
            img_alvo=img_editar,
            desc_alvo="Editar Voto",
            img_confirmacao=img_word,
            desc_confirmacao="Abrir Word",
            timeout=10,
            max_tentativas=10
        )

        if not sucesso_editar:
            return False

        # 3. Clicar em Abrir Word -> Não tem confirmação (O Word vai abrir sozinho)
        # Colocamos apenas 3 tentativas porque não depende da internet carregar, só do clique
        clicar_com_retry(
            img_alvo=img_word,
            desc_alvo="Abrir Word",
            timeout=5,
            max_tentativas=3
        )
        
        return True

    except Exception as e:
        print(f"Erro inesperado na automação: {e}")
        return False