import os
import time
import pyautogui
import pygetwindow as gw
import pyperclip
import FreeSimpleGUI as sg
from icecream import ic

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from nup_poder_judiciario import NumeroUnicoProcesso as nup
from processos.models import Processo
from .ferramentas_selenium import WebBot, Acao

class GEBot:
    # =========================================================================
    # CONFIGURAÇÕES E MAPEAMENTO DE ELEMENTOS (URLs, XPaths e Imagens)
    # =========================================================================
    
    # URLs
    URL_LOGIN = "https://gabinete-eletronico.tst.jus.br/"
    URL_GERENCIAL = "https://gabinete-eletronico.tst.jus.br/escaninho/gerencial"
    
    # XPaths
    XPATH_USER = '//*[@id="user"]'
    XPATH_PASSWORD = '//*[@id="password"]'
    XPATH_BTN_ENTRAR = '//*[@id="logar"]'
    XPATH_INPUT_LOCALIZACAO = '//*[@id="localizacao"]/div/input'
    XPATH_BTN_ENTRAR_LOCALIZACAO = '//*[@id="escolher-localizacao"]'
    XPATH_MENU_RAPIDO_1 = '//*[@id="menu-rapido"]/li[1]'
    XPATH_BTN_MOSTRAR_TODOS = '//*[@id="panel1a-header"]/div[1]/span/button'
    XPATH_BTN_CONSULTA = '//*[@id="app-bar"]/header/div/div[2]/span/div[7]/div/button'
    XPATH_INPUT_NUMERO = '//*[@id="numero"]'

    # Imagens (Usando raw strings 'r' para evitar problemas com barras no Windows)
    DIR_IMG = r"C:\Pendrive\Python\projetos\django\jarvis\mppf\services\assets"
    
    IMG_GMKA = rf"{DIR_IMG}\gmka.png"
    IMG_PESQUISAR = rf"{DIR_IMG}\pesquisar.png"
    IMG_FORA_FLUXO = rf"{DIR_IMG}\fora_do_fluxo.png"
    IMG_REGISTRO = rf"{DIR_IMG}\registro.png"
    IMG_EDITAR_DECISAO = rf"{DIR_IMG}\editar_decisao.png"
    IMG_ABRE_WORD = rf"{DIR_IMG}\abre_word.png"
    IMG_PONTO_INSERCAO = rf"{DIR_IMG}\ponto_insercao.png"
    # IMG_ARQUIVO_CONFIAVEL = rf"{DIR_IMG}\arquivo_confiavel.png"

    # =========================================================================

    def __init__(self, imprimir_manipulacao=True, tempo_de_espera=60):
        self.imprimir_manipulacao = imprimir_manipulacao
        self.tempo_de_espera = tempo_de_espera
        self.wb = WebBot(janela_inicio="max")
        self.driver = self.wb.start_driver()
        self.exclusao = ''''''

    def lista_exclusao(self):
        return self.exclusao.splitlines()

    ###########################################################################
    # Pyautogui tools
    ###########################################################################
    def locate_center_on_screen(self, img):
        try:
            return pyautogui.locateCenterOnScreen(img, confidence=0.7)
        except pyautogui.ImageNotFoundException:
            return None

    def checa_elemento_aberto(self, img, nome, limite=20):
        elemento = self.locate_center_on_screen(img)
        t = 0
        while not elemento:
            time.sleep(1)
            elemento = self.locate_center_on_screen(img)
            ic(nome, t)
            t += 1
            if t >= limite:
                escolha = sg.popup_ok_cancel(
                    f"O elemento {nome} não se encontra visível.\n"
                    f"Navegue até ele e clique em OK.\n"
                    f"Clique em Cancel caso queria pular o processo.",
                    title="Minuta",
                    keep_on_top=True
                )
                if escolha == 'Cancel':
                    return False
        return elemento

    ###########################################################################
    # Login
    ###########################################################################
    def _espera_e_clica(self, xpath):
        """Método auxiliar interno para reduzir repetição de código no Selenium"""
        elemento = WebDriverWait(self.driver, self.tempo_de_espera).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        elemento.click()
        return elemento

    def _espera_e_digita(self, xpath, texto):
        """Método auxiliar interno para reduzir repetição de código no Selenium"""
        elemento = WebDriverWait(self.driver, self.tempo_de_espera).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        elemento.send_keys(texto)
        return elemento

    def digita_cpf(self):
        print('digita_cpf')
        self._espera_e_digita(self.XPATH_USER, os.getenv("CPF"))
    
    def digita_senha(self):
        print('digita_senha')
        self._espera_e_digita(self.XPATH_PASSWORD, os.getenv("PASS"))
    
    def clica_em_entrar(self):
        print('clica_em_entrar')
        self._espera_e_clica(self.XPATH_BTN_ENTRAR)
    
    def clica_em_localizacao(self):
        print('clica_em_localizacao')
        # Usando JS click conforme seu código original
        elemento = WebDriverWait(self.driver, self.tempo_de_espera).until(
            EC.element_to_be_clickable((By.XPATH, self.XPATH_INPUT_LOCALIZACAO))
        )
        self.driver.execute_script("arguments[0].click();", elemento)
    
    def clica_em_GDCPRB(self):
        print('clica_em_GDCPRB')
        elemento = self.checa_elemento_aberto(img=self.IMG_GMKA, nome='GMKA')
        pyautogui.click(elemento)        
    
    def clica_em_entrar_localizacao(self):
        print('clica_em_entrar')
        self._espera_e_clica(self.XPATH_BTN_ENTRAR_LOCALIZACAO)
    
    def login(self):
        self.driver.get(self.URL_LOGIN)
        self.digita_cpf()
        self.digita_senha()
        self.clica_em_entrar()
        
        WebDriverWait(self.driver, self.tempo_de_espera).until(
            EC.element_to_be_clickable((By.XPATH, self.XPATH_MENU_RAPIDO_1))
        )
        self.driver.get(self.URL_GERENCIAL)
        pyautogui.alert('Clique quando a página gerencial terminar de abrir GE.')

    def seleciona_gabinete(self):
        sg.popup_yes_no("Selecionar o gabinete a ser usado")
    
    ###########################################################################
    # Abre a Minuta
    ###########################################################################
    def clica_em_mostrar_todos_os_processos(self):
        print('clica_em_mostrar_todos_os_processos')
        elemento = WebDriverWait(self.driver, self.tempo_de_espera).until(
            EC.element_to_be_clickable((By.XPATH, self.XPATH_BTN_MOSTRAR_TODOS))
        )
        self.driver.execute_script("arguments[0].click();", elemento)

    def clica_em_consulta_processos(self):
        print('clica_em_consulta_processos')
        self._espera_e_clica(self.XPATH_BTN_CONSULTA)
    
    def digita_numero_processo(self, numero):
        print('digita_numero_processo')
        os.system("echo %s| clip" % numero.strip())
        campo = WebDriverWait(self.driver, self.tempo_de_espera).until(
            EC.element_to_be_clickable((By.XPATH, self.XPATH_INPUT_NUMERO))
        )
        campo.click()
        time.sleep(1)
        campo.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)

    def clica_em_pesquisar(self):
        print('clica_em_pesquisar')
        self.checa_elemento_aberto(img=self.IMG_PESQUISAR, nome='Pesquisar', limite=60)
        elemento = self.checa_elemento_aberto(img=self.IMG_PESQUISAR, nome='Pesquisar')
        pyautogui.click(elemento)
        time.sleep(1)
        
    def fecha_fora_do_fluxo(self):
        self.checa_elemento_aberto(img=self.IMG_FORA_FLUXO, nome='Fora do fluxo', limite=60)
        elemento = self.checa_elemento_aberto(img=self.IMG_FORA_FLUXO, nome='Fora do fluxo')
        pyautogui.click(elemento)
        time.sleep(1)

    def abre_minuta(self):
        print('abre_minuta')
        self.checa_elemento_aberto(img=self.IMG_REGISTRO, nome='Registro', limite=60)
        
        elemento_editar = self.checa_elemento_aberto(img=self.IMG_EDITAR_DECISAO, nome='Editar Decisão')
        pyautogui.click(elemento_editar)
        time.sleep(1)
        
        elemento_word = self.checa_elemento_aberto(img=self.IMG_ABRE_WORD, nome='Abre Word')
        time.sleep(1)
        pyautogui.click(elemento_word)
        time.sleep(2) # Ajustado um pouco o tempo para garantir a transição

    def seleciona_processo(self, numero):
        self.clica_em_consulta_processos()
        self.digita_numero_processo(numero=numero)
        self.clica_em_pesquisar()
        self.abre_minuta()

    ###########################################################################
    # Manipula a Minuta
    ###########################################################################
    def esta_minuta_aberta(self):
        ic('esta_minuta_aberta')
        janelas = pyautogui.getAllTitles()
        for janela in janelas:
            if 'Word' in janela and ('AIRR' in janela):
                return janela
        return False

    def pega_janela_word(self):
        ic('pega_janela_word')
        janela = self.esta_minuta_aberta()
        if janela:
            try:
                gw.getWindowsWithTitle(janela)[0].maximize()
                gw.getWindowsWithTitle(janela)[0].activate()
            except Exception:
                pass  

    def extrai_numero_da_janela(self, janela):
        ic('extrai_numero_da_janela')
        return nup(janela).formatado()

    def encontra_ponto_de_insercao_do_DA(self, tempo=0.25):
        ic('encontra_ponto_de_insercao_do_DA')
        time.sleep(1)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(tempo)
        pyautogui.write('!@#$%')
        time.sleep(tempo)
        pyautogui.hotkey('enter')
        time.sleep(tempo)
        
        elemento = self.checa_elemento_aberto(img=self.IMG_PONTO_INSERCAO, nome="Ponto de Inserção")
        if elemento:
            pyautogui.hotkey('esc')
            time.sleep(tempo)
            return True
        return False

    def insere_decisao_de_admissibilidade(self, texto, tempo=0.1):
        ic('insere_decisao_de_admissibilidade')
        pyperclip.copy(texto)
        time.sleep(tempo)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1)
        pyautogui.hotkey('alt', 'f4')
        time.sleep(1)
        pyautogui.hotkey('enter')

    def lanca_DA(self):
        while not self.esta_minuta_aberta():
            time.sleep(1)            
        janela = self.esta_minuta_aberta()
        
        if janela:
            print('#'*120)
            numero = self.extrai_numero_da_janela(janela)            
            ic(numero)
            processo = Processo.objects.filter(numero=numero, classe__nome="AIRR", triagem_mppf__isnull=False).first()
            self.pega_janela_word()
            continuar = self.encontra_ponto_de_insercao_do_DA()
            if continuar:
                self.insere_decisao_de_admissibilidade(texto=processo.triagem_mppf.texto_despacho_admissibilidade, tempo=1)
            else:
                return False
            
            processo.triagem_mppf.foi_lancada_DA_no_GE = True
            processo.triagem_mppf.save()
            ic(f'Foi salvo como feito o processo: {numero}')
            print('#'*120)
            return numero
        return False