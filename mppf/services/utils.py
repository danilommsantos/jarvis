import ctypes
import os
import pyautogui
import pygetwindow as gw
import re
import time
import win32gui

from icecream import ic
from pathlib import Path


def limpar_texto(texto):
    texto = texto.replace('\xa0', ' ')
    texto = texto.replace('\r\n', '\n')
    texto = re.sub(r'[ \t]+\n', '\n', texto)
    texto = re.sub(r'\n\s*\n', '\n\n', texto)
    return texto.strip()


def esta_aberta_a_janela(titulo_da_janela):
    # ic(titulo_da_janela)
    janelas = pyautogui.getAllTitles()
    # ic(janelas)
    for janela in janelas:
        if titulo_da_janela in janela:
            return True
    return False


def existe_o_arquivo(caminho):
    if os.path.isfile(caminho):
        return True
    return False


def nome_da_janela_ativa():
    # Obtém o handle da janela ativa
    hwnd = win32gui.GetForegroundWindow()
    # Obtém o título da janela ativa
    janela_ativa = win32gui.GetWindowText(hwnd)
    ic(janela_ativa)
    return janela_ativa


def muda_foco_para_janela(titulo):
    janelas = pyautogui.getAllTitles()
    ic(titulo)
    titulo_completo = next((s for s in janelas if titulo in s), None)
    ic(titulo_completo)
    for i in range(20):
        ic(i)
        try:
            janelas = gw.getWindowsWithTitle(titulo_completo)
            if janelas:
                janelas[0].activate()
            else:
                print("Pygetwindow não encontrou nenhuma janela com o título fornecido.")            
        except:
            pass  # Pulando o erro que não está claro na documentação da biblioteca.            
        if "PDF-XChange Viewer" not in nome_da_janela_ativa():
            print('pygetwindow não funcionou.')        
            # pyautogui.getWindowsWithTitle(titulo_completo)[0].maximize()
            if "PDF-XChange Viewer" not in nome_da_janela_ativa():
                print('pyautogui não funcionou.')
                # Traz a janela para o foco
                hwnd = win32gui.FindWindow(None, titulo_completo)
                ic(hwnd)
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                else:
                    print("Handle da janela não encontrado.")
                if "PDF-XChange Viewer" not in nome_da_janela_ativa():
                    print('win32gui não funcionou.')            
                    print('Não foi possível mudar o foco da janela.')            
            else:
                print('pyautogui funcionou.')
        else:
            print('pygetwindow funcionou.')
            
        time.sleep(1)
        if not titulo_completo or titulo_completo.lower() == gw.getActiveWindowTitle().title().lower():
            break
    if titulo_completo and titulo_completo.lower() != gw.getActiveWindowTitle().title().lower():
        pyautogui.alert('Mudar manualmente o foco para PDF-XChange Viewer.')

def abre_arquivo(caminho):
    if existe_o_arquivo(caminho):
        try:
            os.startfile(caminho, 'open')
        except:
            pass
            # pyautogui.alert(text='caminho', title='O arquivo não pode ser aberto.', button='OK')
    else:
        print('Baixar.')
        # pyautogui.alert(text=caminho, title='O arquivo não existe.', button='OK')
    
def pdf_mais_recente(diretorio, expressao):
    # Obtém todos os arquivos PDF no diretório que contêm a expressão no nome
    arquivos = [f for f in Path(diretorio).glob('*.pdf') if expressao in f.name] 
    # Verifica se há arquivos correspondentes
    if not arquivos:    
        pyautogui.alert(text=expressao, title='O arquivo não existe. !', button='OK')    
        return diretorio    
    # Retorna o arquivo mais recente com base na data de modificação
    arquivo_mais_recente = max(arquivos, key=os.path.getmtime)
    return arquivo_mais_recente

