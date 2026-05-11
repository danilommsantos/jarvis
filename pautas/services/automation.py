import os
import time
import pyautogui
import pygetwindow as gw
import pyperclip
from PIL import ImageGrab
from django.conf import settings

TABS_ATE_BOTAO_BUSCAR = 8

def localizar_na_tela(caminho_imagem):
    """
    Função auxiliar que tira o print de múltiplos monitores
    e devolve a posição do botão, ignorando erros menores.
    """
    try:
        tela = ImageGrab.grab(all_screens=True)
        return pyautogui.locate(caminho_imagem, tela, confidence=0.8, grayscale=True)
    except pyautogui.ImageNotFoundException:
        return None
    except Exception as e:
        print(f"Erro inesperado ao localizar imagem '{caminho_imagem}': {e}")
        return None

def clicar_com_retry(img_alvo, desc_alvo, img_confirmacao=None, desc_confirmacao=None, confirmacao_fn=None, acao_extra=None, timeout=1, max_tentativas=5):
    """
    1. Encontra e clica na imagem alvo.
    2. Opcional: Executa uma ação extra (como colar texto).
    3. Opcional: Aguarda confirmação por imagem (img_confirmacao) e/ou por função (confirmacao_fn).
    4. Se a confirmação não aparecer, tenta o processo todo de novo (até max_tentativas).
    """
    for tentativa in range(1, max_tentativas + 1):
        print(f"\n--- [Tentativa {tentativa}/{max_tentativas}] Clicando em '{desc_alvo}' ---")

        # PASSO 1: Encontrar e clicar no botão alvo
        start_busca = time.time()
        clicou = False

        while time.time() - start_busca < timeout:
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
            continue

        # PASSO 2: Ação extra opcional (ex: Colar número e dar Enter)
        if acao_extra:
            time.sleep(0.5)
            acao_extra()

        # PASSO 3: Se não há confirmação configurada, consideramos um sucesso
        if not img_confirmacao and not confirmacao_fn:
            return True

        # PASSO 4: Aguardar confirmação por imagem e/ou por função
        print(f" > Aguardando '{desc_confirmacao}' (Timeout de {timeout}s)...")
        start_espera = time.time()
        confirmado = False

        while time.time() - start_espera < timeout:
            if img_confirmacao and localizar_na_tela(img_confirmacao):
                print(f" V Imagem de referência '{desc_confirmacao}' confirmada!")
                confirmado = True
                break
            if confirmacao_fn and confirmacao_fn():
                print(f" V Confirmação alternativa de '{desc_confirmacao}' detectada!")
                confirmado = True
                break
            time.sleep(0.5)

        if confirmado:
            return True
        else:
            print(f" X Timeout: '{desc_confirmacao}' não apareceu. Repetindo clique inicial...")

    print(f"!!! Falha Crítica: Esgotadas as {max_tentativas} tentativas para a ação '{desc_alvo}'.")
    return False



def word_aberto(numero_processo):
    print(gw.getWindowsWithTitle('Word'))
    for w in gw.getWindowsWithTitle('Word'):
        if numero_processo in w.title:
            print(w.title)
            return True
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

        for img in [img_consulta, img_editar, img_word]:
            if not os.path.exists(img):
                print(f"ERRO: Imagem não encontrada no caminho -> {img}")
                return False

        # --- AÇÕES DA AUTOMAÇÃO ---

        pyperclip.copy(numero_processo)

        def acao_colar_e_buscar():
            pyautogui.hotkey('ctrl', 'v')
            for _ in range(TABS_ATE_BOTAO_BUSCAR):
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

        
        # 2. Clicar em Editar Voto -> Confirmar via imagem OU via Word já aberto
        sucesso_editar = clicar_com_retry(
            img_alvo=img_editar,
            desc_alvo="Editar Voto",
            img_confirmacao=img_word,
            desc_confirmacao="Abrir Word ou Word aberto",
            confirmacao_fn=lambda: word_aberto(numero_processo),
            timeout=10,
            max_tentativas=10
        )

        if not sucesso_editar:
            return False

        print(f" > Aguardando Word abrir para o processo {numero_processo}...")
        start_word = time.time()
        while time.time() - start_word < 30:
            if word_aberto(numero_processo):
                print(f" V Word aberto com sucesso para o processo {numero_processo}.")
                return True
            time.sleep(1)

        print(f"!!! Timeout: Word não abriu para o processo {numero_processo}.")
        return False

    except Exception as e:
        print(f"Erro inesperado na automação: {e}")
        return False