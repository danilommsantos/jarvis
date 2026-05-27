from .utils import esta_aberta_a_janela, existe_o_arquivo, pdf_mais_recente
from django.db.models.functions import Length
from mppf.models import ExpressaoMateria, ExpressaoMarcador
from nup_poder_judiciario import NumeroUnicoProcesso as Nup
from pypdf import PdfReader, PdfWriter
from tqdm import tqdm
import fitz  # PyMuPDF
import FreeSimpleGUI as sg
import os
import pyautogui
import PyPDF2
import re
import subprocess
import time

PDFXCHANGE_EXE = r'C:\Pendrive\Programas\Tracker Software\PDF Viewer\PDFXCview.exe'

# ==========================================
# NOVA SEÇÃO: Controle de Arquivos Anotados
# ==========================================
ANOTADOS_PATH = r'C:\Pendrive\Python\projetos\django\jarvis\mppf\services\assets\anotados.txt'


def carregar_pdfs_anotados():
    """Carrega a lista de PDFs que já foram destacados a partir do arquivo txt."""
    try:
        with open(ANOTADOS_PATH, 'r', encoding='utf-8') as arquivo:
            return [linha.strip() for linha in arquivo.readlines()]
    except FileNotFoundError:
        return []


def registrar_pdf_anotado(pdf_path):
    """Adiciona o caminho do PDF processado ao arquivo txt."""
    try:
        with open(ANOTADOS_PATH, 'a', encoding='utf-8') as arquivo:
            arquivo.write(f"{pdf_path}\n")
    except Exception as e:
        print(f"Erro ao registrar no txt: {e}")
# ==========================================


def pagina_da_DA(caminho):
    with open(caminho, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        pag_DA = 1
        decisoes_de_admissibilidade = [m for m in pdf_reader.outline if (not isinstance(m, list)) and ("Despacho de Admissibilidade" == m["/Title"])]
        if decisoes_de_admissibilidade:
            pag_DA = pdf_reader.get_destination_page_number(decisoes_de_admissibilidade[-1]) + 1
        else:
            decisoes_de_admissibilidade = [m for m in pdf_reader.outline if " - Decisão - " in m["/Title"] or '- Decisão (Decisão Recurso de Revista)' in m["/Title"]]
            lista_RRs = [m for m in pdf_reader.outline if " - Recurso de Revista" in m["/Title"]]
            if len(lista_RRs) > 0:
                pag_DA = pdf_reader.get_destination_page_number(lista_RRs[-1]) + 1
            for decisao in decisoes_de_admissibilidade:
                if pdf_reader.get_destination_page_number(decisao) + 1 > pag_DA:
                    pag_DA = pdf_reader.get_destination_page_number(decisao) + 1
                    break      
    return pag_DA


def verifica_decisao_anterior(caminho):
    try:
        with open(caminho, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for marcador in pdf_reader.outline:
                if not isinstance(marcador, list) and ('(Decisão GE)' in marcador['/Title'] or 'TST - Decisão/Despacho' in marcador['/Title']):
                    pyautogui.alert(text=f'{marcador["/Title"]}', title='Verificar', button='OK')
    except FileNotFoundError:
        print(f"Arquivo PDF não encontrado: {caminho}")


def abre_a_pagina_da_DA(caminho):
    continuar = True
    tentativa = 0
    limite = 2
    while continuar:
        pyautogui.hotkey('ctrl', 'shift', 'n')
        try:
            pyautogui.locateCenterOnScreen(
                r'C:\Pendrive\Python\projetos\django\jarvis\mppf\services\assets\ir_para_pagina.png', 
                confidence=0.6415
                )
            continuar = False
        except pyautogui.ImageNotFoundException:
            tentativa += 1
            if tentativa > limite:
                continuar = False
            print(f'Ir para a página não foi encontrado. Tentativa {tentativa}.')
        time.sleep(1)
    pyautogui.write(str(pagina_da_DA(caminho=caminho)))
    pyautogui.press('enter')

    
def maximiza_aba():
    time.sleep(0.5)
    try:
        maximizar = pyautogui.locateCenterOnScreen('C:\\Pendrive\\Python\\code\\django\\mppf\\main\\auto_img\\maximizar.png', confidence=0.8)
        pyautogui.click(maximizar)
    except pyautogui.ImageNotFoundException:
        print('Imagem não encontrada.')


def encontrar_marcadores(pdf_path, expressoes):
    doc = fitz.open(pdf_path)
    marcadores = doc.get_toc(simple=True)
    total_paginas = doc.page_count # Necessário para caso o marcador seja o último
    resultados = []
    
    for i, marcador in enumerate(marcadores):
        titulo, pagina = marcador[1], marcador[2]
        for expressao in expressoes:
            if expressao in titulo:
                # Ajuste de índice (TOC retorna base 1, PyMuPDF exige base 0)
                pag_inicial = pagina - 1 
                # Evita erro de tipo "None" no range() se for o último marcador
                proxima_pagina = marcadores[i + 1][2] - 1 if i + 1 < len(marcadores) else total_paginas
                resultados.append((pag_inicial, proxima_pagina))
                break
    doc.close()
    return resultados


def destaca_texto_pdf(pdf_path):
    print('destaca_texto_pdf')
    
    # 1. Verifica no TXT primeiro (mais rápido que abrir o PDF)
    # anotados = carregar_pdfs_anotados()
    pdf = str(pdf_path).replace("D:/Processos/", "")
    pdf = pdf.replace("D:\\Processos\\", "")
    # if pdf in anotados:
    #     print(f'{pdf_path} já está no registro de anotados (txt). Pulando destaque.')
    #     return

    # 2. Verifica nos metadados
    # print(foi_pdf_destacado(pdf_path=pdf_path))
    # if not foi_pdf_destacado(pdf_path=pdf_path):
    if True:
        pecas = encontrar_marcadores(pdf_path=pdf_path, expressoes=[
            "- Decisão (Decisão Recurso de Revista)", 
            "- Acórdão -", 
            "Acórdão TRT", 
            "Despacho de Admissibilidade",
            ])
        print(len(pecas))
        print(pecas)               
        doc = fitz.open(pdf_path)
        expressoes = ExpressaoMateria.objects.annotate(
                tamanho=Length('texto')
            ).order_by('-tamanho')
        # print(expressoes)
        
        for peca in pecas:
            pagina_inicial, pagina_final = peca
            for numero_pagina in tqdm(range(pagina_inicial, pagina_final)):
                pagina = doc[numero_pagina]
                
                # 1. Extrai o texto puro da página para o Regex analisar
                texto_pagina = pagina.get_text("text") 
                
                for expressao in expressoes:
                    # 1. Verifica se a expressão do banco já é um Regex pronto
                    if expressao.usar_regex:
                        padrao_regex = expressao.texto
                    else:
                        # Se não for regex, faz o escape e lida com os espaços em branco
                        palavras = expressao.texto.split()
                        palavras_escapadas = [re.escape(p) for p in palavras]
                        padrao_base = r"\s+".join(palavras_escapadas)
                        inicio = r"\b" if re.match(r'\w', expressao.texto[0]) else r""
                        fim = r"\b" if re.search(r'\w$', expressao.texto) else r""
                        padrao_regex = inicio + padrao_base + fim
                    
                    # Usamos um set para evitar buscar a mesma string duas vezes na mesma página
                    textos_para_destacar = set()
                    
                    # 2. O Regex procura no texto da página e pesca a string com a formatação REAL do PDF
                    for match in re.finditer(padrao_regex, texto_pagina, flags=re.IGNORECASE):
                        texto_normalizado = re.sub(r'\s+', ' ', match.group()).strip()
                        textos_para_destacar.add(texto_normalizado)
                    
                    # 3. Agora passamos a string literal encontrada para o search_for do PyMuPDF
                    for texto_exato in textos_para_destacar:
                        text_instances = pagina.search_for(texto_exato, flags=fitz.TEXT_DEHYPHENATE)
                        
                        for inst in text_instances:
                            highlight = pagina.add_highlight_annot(inst)
                            # cor_sem_hash = expressao.assunto.cor.replace('#', '')
                            cor_sem_hash = "FFFF00"
                            color_rgb = tuple(int(cor_sem_hash[i:i + 2], 16) / 255 for i in (0, 2, 4))
                            highlight.set_colors(stroke=color_rgb)
                            highlight.update()
        
        doc.saveIncr()
        doc.close()        
        marcar_como_destacado(pdf_path=pdf_path)
        
        # 3. Adiciona ao arquivo TXT após o sucesso
        registrar_pdf_anotado(pdf)
        print(f'PDF destacado e adicionado ao registro: {pdf_path}')
    else:
        # Se estava destacado nos metadados mas não no TXT, atualizamos o TXT para sincronizar
        registrar_pdf_anotado(pdf_path)
        print(f'{pdf_path} já foi destacado (via metadado). Sincronizado com o txt.')

            
def foi_pdf_destacado(pdf_path):
    print('foi_pdf_destacado')
    doc = fitz.open(pdf_path)
    metadados = doc.metadata
    doc.close() # Movido para depois de extrair os metadados
    print(metadados.get('author', ''))
    if 'Destacado' in metadados.get('author', ''):
        return True
    return False


def marcar_como_destacado(pdf_path):
    print("marcar_como_destacado")
    pdf_documento = fitz.open(pdf_path)
    metadados = pdf_documento.metadata
    autor_original = metadados.get("author", "")
    novo_autor = f"{autor_original} Destacado" if autor_original else "Destacado"
    metadados["author"] = novo_autor
    pdf_documento.set_metadata(metadados)
    pdf_documento.saveIncr()
    pdf_documento.close()


def negritar_marcadores(pdf):
    expressions = ExpressaoMarcador.objects.all()
    try:
        with open(pdf, "rb") as f:
            reader = PdfReader(f)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            def process_bookmarks(bookmarks, parent=None):
                for bm in tqdm(bookmarks):
                    if isinstance(bm, list):
                        process_bookmarks(bm, parent)
                    else:
                        title = bm.title
                        try:
                            page_number = reader.get_destination_page_number(bm)
                            bold = bm.font_format == 2 or any(
                                re.search(re.escape(exp.texto), title, re.IGNORECASE) for exp in expressions)
                            writer.add_outline_item(title, page_number, parent=parent, bold=bold)
                        except Exception as e:
                            print(f"Erro no marcador '{title}' em {pdf}: {e}")

            if reader.outline:
                process_bookmarks(reader.outline)

        with open(pdf, "wb") as output_file:
            writer.write(output_file)

    except Exception as e:
        print(f"Erro crítico no arquivo {pdf}: {e}")
        raise e


def fechar_documento_pdfxchange():
    """Fecha o documento ativo no PDF-XChange Viewer (Ctrl+W) sem fechar a aplicação."""
    import ctypes
    import win32api
    import win32con
    import win32gui

    hwnd = None

    def _cb(h, _):
        nonlocal hwnd
        if win32gui.IsWindowVisible(h) and 'PDF-XChange Viewer' in win32gui.GetWindowText(h):
            hwnd = h
        return True

    win32gui.EnumWindows(_cb, None)

    if not hwnd:
        print('[pdf] PDF-XChange Viewer não encontrado — nada a fechar.')
        return

    # Traz ao foco sem alterar tamanho: só restaura se estiver minimizada
    if ctypes.windll.user32.IsIconic(hwnd):
        ctypes.windll.user32.ShowWindow(hwnd, 9)   # SW_RESTORE (apenas se minimizada)
    else:
        ctypes.windll.user32.ShowWindow(hwnd, 5)   # SW_SHOW (mantém maximizada/normal)
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    win32api.keybd_event(0x11, 0, 0, 0)                          # Ctrl ↓
    win32api.keybd_event(ord('W'), 0, 0, 0)                      # W ↓
    win32api.keybd_event(ord('W'), 0, win32con.KEYEVENTF_KEYUP, 0)  # W ↑
    win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl ↑
    print('[pdf] documento ativo fechado.')


def _hwnd_pdfxchange():
    """Retorna o handle da janela principal do PDF-XChange Viewer, ou None."""
    import win32gui
    result = []

    def _cb(h, _):
        if win32gui.IsWindowVisible(h) and 'PDF-XChange Viewer' in win32gui.GetWindowText(h):
            result.append(h)
        return True

    win32gui.EnumWindows(_cb, None)
    return result[0] if result else None


def _scroll_marcador_topo(hwnd):
    """
    Rola o painel DSUI:BookmarksView para que o marcador da DA
    (que o PDF-XChange deixa na parte inferior) apareça no topo.

    Estratégia: envia WM_VSCROLL / SB_LINEDOWN ao DSUI:BookmarksView
    tantas vezes quantas linhas cabem no painel (altura ÷ altura estimada
    do item), movendo o marcador selecionado do fundo para o topo.
    """
    import ctypes
    import win32gui

    WM_VSCROLL  = 0x0115
    SB_LINEDOWN = 1
    ITEM_HEIGHT_PX = 20   # altura estimada de cada marcador em pixels

    bookmarks_hwnd = None

    def _find_bm(h, _):
        nonlocal bookmarks_hwnd
        if win32gui.GetClassName(h) == 'DSUI:BookmarksView':
            bookmarks_hwnd = h
        return True

    win32gui.EnumChildWindows(hwnd, _find_bm, None)
    if not bookmarks_hwnd:
        print('[pdf] DSUI:BookmarksView não encontrado.')
        return

    rect   = win32gui.GetWindowRect(bookmarks_hwnd)
    altura = rect[3] - rect[1]
    n      = max(1, (altura // ITEM_HEIGHT_PX) - 1)

    for _ in range(n):
        ctypes.windll.user32.PostMessageW(bookmarks_hwnd, WM_VSCROLL, SB_LINEDOWN, 0)

    print(f'[pdf] Marcador da DA rolado para o topo ({n} linhas).')


def _navegar_pagina(pagina):
    """
    Aguarda o documento carregar e navega para a página via Ctrl+Shift+N.
    Roda em thread separada para não bloquear.
    """
    import ctypes
    import win32api
    import win32con

    time.sleep(1.5)  # aguarda o PDF carregar na aba

    hwnd = _hwnd_pdfxchange()
    if not hwnd:
        return

    ctypes.windll.user32.SetForegroundWindow(hwnd)
    time.sleep(0.15)

    # Ctrl+Shift+N → diálogo "Ir para página"
    for vk, down in [
        (0x11, True), (0x10, True), (0x4E, True),   # Ctrl+Shift+N press
        (0x4E, False), (0x10, False), (0x11, False),  # release
    ]:
        flag = 0 if down else win32con.KEYEVENTF_KEYUP
        win32api.keybd_event(vk, 0, flag, 0)

    time.sleep(0.25)  # aguarda o diálogo abrir

    # Digita o número e confirma
    for char in str(pagina):
        vk = ord(char)
        win32api.keybd_event(vk, 0, 0, 0)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

    win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
    print(f'[pdf] navegado para página {pagina}.')

    # Aguarda o PDF-XChange sincronizar a seleção do marcador e rola para o topo
    time.sleep(0.8)
    _scroll_marcador_topo(hwnd)


def abre_pdf_na_pagina(caminho, pagina):
    """
    Abre o PDF na instância existente do PDF-XChange (sem criar nova janela)
    e navega para a página da DA em background.
    """
    import threading

    fechar_documento_pdfxchange()

    # os.startfile reutiliza a instância já aberta — sem nova janela, sem redimensionamento
    os.startfile(str(caminho))

    threading.Thread(target=_navegar_pagina, args=(pagina,), daemon=True).start()


def abre_pdf_do_processo(processo, pasta_processos):
    print(processo.numero)
    caminho = pdf_mais_recente(diretorio=pasta_processos, expressao=processo.numero)
    print(caminho)
    if esta_aberta_a_janela(titulo_da_janela=f'{processo.numero} - PDF-XChange Viewer') or esta_aberta_a_janela(titulo_da_janela=f'{processo.numero}* - PDF-XChange Viewer'):
        print('O arquivo já está aberto.')
    elif existe_o_arquivo(caminho):
        negritar_marcadores(pdf=caminho)
        destaca_texto_pdf(pdf_path=caminho)
        pagina = pagina_da_DA(caminho=caminho)
        print(f'Abrindo na página {pagina}...')
        abre_pdf_na_pagina(caminho=caminho, pagina=pagina)
    else:
        print(processo.numero, 'não existe em', pasta_processos)