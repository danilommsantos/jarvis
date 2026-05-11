import time
import os
import traceback
import FreeSimpleGUI as sg

from bs4 import BeautifulSoup
from bs4.element import Comment
from icecream import ic
from selenium import webdriver as wb
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait


class Acao_Indisponivel_Error(Exception):
    pass

class Acao:
    """
    Conjunto de ações de manipulação de elemento disponíveis.
    """
    DIGITAR = "digitar"
    CLICAR = 'clicar'
    COLAR = 'colar'
    EXTRAIR_LINK = 'extrair_link'
    PAGE_SOURCE = 'page_source'
    GET_BODY_TEXT = 'extrai_texto'
    SELECIONAR_OPCAO = 'selecionar_opcao'


class WebBot:
    def __init__(
        self,
        pasta_downloads="C:\\Users\\danil\\Downloads",
        usar_proxy=False,
        proxy="proxyserver.rede.tst:3128",
        janela_inicio="min",
        chromedriver_path="C:\\Pendrive\\BD\\Chromedriver\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe",
    ):
        self.pasta_downloads = pasta_downloads.replace('/', '\\')
        self.usar_proxy = usar_proxy
        self.proxy = proxy
        self.janela_inicio = janela_inicio
        self.chromedriver_path = chromedriver_path

    def start_driver(self):
        """Retorna o webdriver do chrome."""
        driver = wb.Chrome(options=self.options())
        # driver.implicitly_wait(10)
        if self.janela_inicio == "max":
            driver.maximize_window()
        elif self.janela_inicio == "min":
            driver.minimize_window()
        return driver

    def options(self):
        options = wb.ChromeOptions()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        preferencias = {"download.default_directory": self.pasta_downloads}
        options.add_experimental_option("prefs", preferencias)
        print(f"Configuração para download realizada! Pasta de destino: {self.pasta_downloads}")
        if self.usar_proxy:
            print("Existe um proxy!")
            options.add_argument("--proxy-server=%s" % self.proxy)
        print("Configuração de proxy realizada!")
        return options

    def tag_visible(self, element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    def text_from_html(self, body):
        soup = BeautifulSoup(body, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(self.tag_visible, texts)
        return u" ".join(t.strip() for t in visible_texts)

    def manipula_elemento(self, descricao, acao, dado, driver, elemento_xpath, tempo=60, imprimir=True):
        if imprimir:
            print(descricao)
        try:
            wait = WebDriverWait(driver, timeout=tempo).until(EC.presence_of_element_located((By.XPATH,
                                                                                              elemento_xpath)))
            # print('Procurando elemento.')
            # element_present = EC.presence_of_element_located((By.XPATH, elemento_xpath))
            # print('Elemento encontrado: ', elemento_xpath)
            # WebDriverWait(driver, timeout=tempo).until(element_present)
            if acao == Acao.DIGITAR:
                # print('Digitando: ', descricao)
                driver.find_element(By.XPATH, elemento_xpath).send_keys(dado)
                # print('Digitado: ', descricao)
            elif acao == Acao.CLICAR:
                driver.find_element(By.XPATH, elemento_xpath).click()

            elif acao == Acao.SELECIONAR_OPCAO:
                select_element = driver.find_element(By.XPATH, elemento_xpath)
                select = Select(select_element)
                for e in select.options:
                    print(e)
                select.select_by_value(dado)

            elif acao == Acao.COLAR:
                os.system("echo %s| clip" % dado.strip())
                el = driver.find_element(By.XPATH, elemento_xpath)
                el.click()
                time.sleep(1)
                el.send_keys(Keys.CONTROL, 'v')
            elif acao == Acao.EXTRAIR_LINK:
                link = driver.find_element(By.XPATH, elemento_xpath).get_attribute('href')
                return driver, link
            elif acao == Acao.PAGE_SOURCE:
                return BeautifulSoup(driver.page_source, 'html.parser')
            else:
                raise Acao_Indisponivel_Error(f"A ação {acao} não está disponível!")
                traceback.print_exc()
            return driver
        except Exception:
            sg.Popup(
                f"Erro! A ação {descricao} não pode ser realizada, porque passou-se tempo demais sem que a "
                f"página fosse carregada."
            )
            traceback.print_exc()
            return driver
