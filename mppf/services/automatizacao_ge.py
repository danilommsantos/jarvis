import os
import time
import threading
import pywintypes
import win32com.client
from icecream import ic
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from nup_poder_judiciario import NumeroUnicoProcesso as nup


class _DriverCompat:
    """Shim para manter compatibilidade com views.py que chama gebot.driver.get(url)."""

    def __init__(self, page):
        self._page = page

    def get(self, url):
        self._page.goto(url)


class GEBot:
    # =========================================================================
    # CONFIGURAÇÕES
    # =========================================================================
    URL_LOGIN = "https://gabinete-eletronico.tst.jus.br/"
    URL_GERENCIAL = "https://gabinete-eletronico.tst.jus.br/escaninho/gerencial"

    TIMEOUT_MS = 60_000   # timeout padrão do Playwright (ms)
    MARCADOR_DA = "!@#$%" # placeholder no documento Word

    # =========================================================================

    def __init__(self, tempo_de_espera=60, log_fn=None):
        self.tempo_de_espera = tempo_de_espera
        # log_fn(msg, sucesso=None) — callback para enviar mensagens ao log SSE
        self._log_fn = log_fn
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-external-protocol-dialog',  # abre Word sem confirmar
            ],
        )
        self.context = self.browser.new_context(no_viewport=True)
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.TIMEOUT_MS)
        self.exclusao = ''''''

    def __del__(self):
        try:
            self.browser.close()
            self._pw.stop()
        except Exception:
            pass

    def _log(self, msg, sucesso=None):
        """Imprime no console e encaminha ao SSE se log_fn foi fornecido."""
        print(msg)
        if self._log_fn:
            self._log_fn(msg, sucesso=sucesso)

    @property
    def driver(self):
        return _DriverCompat(self.page)

    def lista_exclusao(self):
        return self.exclusao.splitlines()

    ###########################################################################
    # Login (SSO → localização → 2FA → gerencial)
    ###########################################################################
    def login(self):
        self._log('[login] navegando para URL de login...')
        self.page.goto(self.URL_LOGIN)

        # SSO — digita CPF e senha caractere a caractere para disparar eventos JS
        self._log('[login] preenchendo CPF...')
        cpf = self.page.get_by_role("textbox", name="Usuário")
        cpf.click()
        cpf.press_sequentially(os.getenv('CPF', ''), delay=50)

        self._log('[login] preenchendo senha...')
        senha = self.page.get_by_role("textbox", name="Senha")
        senha.click()
        senha.press_sequentially(os.getenv('PASS', ''), delay=50)
        senha.press("Enter")

        # Seleção de localização — GDCEBC (ocorre antes do 2FA)
        self._log('[login] clicando no seletor de localização...')
        self.page.locator('#localizacao input').click()
        self._log('[login] aguardando lista de localizações...')
        self.page.get_by_role("list").get_by_text("GDCEBC").wait_for()
        self._log('[login] selecionando GDCEBC...')
        self.page.get_by_role("list").get_by_text("GDCEBC").click()
        self.page.get_by_role("button", name="Escolher").click()
        self._log('[login] localização confirmada.')

        # 2FA — aguarda o usuário preencher o código diretamente na página (2 min)
        self._log('[login] aguardando 2FA (preencha o código diretamente na página)...')
        self.page.get_by_test_id("imagem-menu-rapido-2").wait_for(timeout=120_000)
        self._log('[login] 2FA concluído.', sucesso=True)

        # Navega para a tela gerencial via menu rápido
        self._log('[login] navegando para tela gerencial...')
        self.page.get_by_test_id("imagem-menu-rapido-2").click()
        self.page.wait_for_url(f"**{self.URL_GERENCIAL}**")
        # Aguarda a paginação do escaninho aparecer — confirma carregamento completo
        self._log('[login] aguardando escaninho gerencial carregar...')
        self.page.locator(
            '#paper > div.MuiPaper-root.MuiPaper-elevation.MuiPaper-rounded'
            '.MuiPaper-elevation2.css-110i50s > div > div > '
            'div.footer-escaninho > div > div > '
            'div.MuiTablePagination-root.css-1ixt7qf > div > '
            'p.MuiTablePagination-displayedRows.css-7xvqlb > span > b:nth-child(3)'
        ).wait_for()
        self._log('[login] escaninho pronto.', sucesso=True)

    def seleciona_gabinete(self):
        pass  # incorporado ao login()

    ###########################################################################
    # Abre a Minuta
    ###########################################################################
    def clica_em_consulta_processos(self):
        self._log('[consulta] abrindo consulta de processo...')
        self.page.get_by_role("button", name="Abrir consulta de processo").click()

    def digita_numero_processo(self, numero):
        self._log(f'[consulta] digitando número: {numero}')
        campo = self.page.locator("#numero")
        campo.click()
        campo.fill(numero.strip())

    def clica_em_pesquisar(self):
        self._log('[consulta] clicando em Pesquisar...')
        self.page.get_by_role("dialog").get_by_role("button", name="Pesquisar").click()

    def fecha_modal_consulta(self):
        self._log('[consulta] aguardando resultados carregarem...')
        try:
            self.page.get_by_role("button", name="Editar Decisão", exact=True).wait_for(timeout=30_000)
            self._log('[consulta] resultado carregado.')
        except PlaywrightTimeoutError:
            self._log('[consulta] AVISO — "Editar Decisão" não apareceu antes de fechar o modal.')
        try:
            fechar = self.page.get_by_role("dialog").get_by_role("button", name="FECHAR")
            fechar.wait_for(timeout=3_000)
            self._log('[consulta] fechando modal de consulta...')
            fechar.click()
        except PlaywrightTimeoutError:
            pass  # Modal já fechou automaticamente

    def fecha_fora_do_fluxo(self):
        try:
            self.page.get_by_text('Fora do Fluxo').wait_for(timeout=5_000)
            self._log('[consulta] fechando modal "Fora do Fluxo"...')
            self.page.get_by_role('button', name='Fechar').click()
        except PlaywrightTimeoutError:
            pass

    def abre_minuta(self, numero):
        self._log(f'[minuta] hovering sobre o processo {numero} para revelar botões...')
        self.page.get_by_text(numero, exact=False).first.hover()
        self._log('[minuta] clicando em Editar Decisão...')
        self.page.get_by_role("button", name="Editar Decisão", exact=True).click()
        self._log('[minuta] clique em "Abrir Word" para abrir o documento...')

    def seleciona_processo(self, numero):
        self._log(f'[processo] iniciando seleção: {numero}')
        self.clica_em_consulta_processos()
        self.digita_numero_processo(numero=numero)
        self.clica_em_pesquisar()
        self.fecha_modal_consulta()
        self.fecha_fora_do_fluxo()
        self.abre_minuta(numero)

    ###########################################################################
    # Word via win32com
    ###########################################################################
    def _aguarda_word_com_airr(self, numero_esperado):
        """Aguarda até o Word abrir o documento AIRR do processo esperado. Retorna (word_app, doc) ou (None, None)."""
        self._log(f'[word] aguardando Word abrir documento para {numero_esperado}...')
        deadline = time.monotonic() + self.tempo_de_espera
        while time.monotonic() < deadline:
            try:
                word_app = win32com.client.GetActiveObject("Word.Application")
                for i in range(1, word_app.Documents.Count + 1):
                    try:
                        doc = word_app.Documents(i)
                        if nup(doc.Name).formatado() == numero_esperado:
                            self._log(f'[word] documento encontrado: {doc.Name}')
                            return word_app, doc
                    except (pywintypes.com_error, AttributeError):
                        pass  # documento ainda carregando
            except pywintypes.com_error:
                pass
            time.sleep(0.5)
        self._log(f'[word] timeout — documento do processo {numero_esperado} não encontrado.', sucesso=False)
        return None, None

    def _inserir_no_word(self, word_app, doc, texto):
        """
        Substitui MARCADOR_DA pelo texto no documento Word.
        Usa rng.Text em vez de Find.Execute(ReplaceWith=...) para suportar
        textos longos (Execute limita ReplaceWith a ~255 chars).
        Retorna True em caso de sucesso, False se falhar ou o Word
        tentar salvar em local diferente do original (local vs. rede).
        """
        original_name = doc.FullName
        self._log(f'[word] documento: {doc.Name}')
        word_app.DisplayAlerts = 0  # wdAlertsNone — suprime diálogos de salvamento
        try:
            self._log(f'[word] buscando marcador "{self.MARCADOR_DA}"...')
            rng = doc.Content
            rng.Find.ClearFormatting()
            rng.Find.Text = self.MARCADOR_DA
            found = rng.Find.Execute()

            if not found:
                self._log(f'[word] FALHA — marcador não encontrado em {doc.Name}', sucesso=False)
                doc.Close(SaveChanges=False)
                return False

            # rng agora aponta para o marcador encontrado; substituição sem limite de tamanho
            rng.Text = texto
            self._log('[word] marcador substituído. Salvando...')
            doc.Save()

            # Se o Word redirecionou o salvamento para um caminho local, é falha
            if doc.FullName != original_name:
                self._log(f'[word] FALHA — salvo em local diferente: {doc.FullName}', sucesso=False)
                doc.Close(SaveChanges=False)
                return False

            self._log('[word] salvo com sucesso. Fechando documento...', sucesso=True)
            doc.Close(SaveChanges=False)
            return True

        except Exception as e:
            self._log(f'[word] ERRO — {e}', sucesso=False)
            try:
                doc.Close(SaveChanges=False)
            except Exception:
                pass
            return False
        finally:
            try:
                word_app.DisplayAlerts = -1  # wdAlertsAll
            except Exception:
                pass

    def lanca_DA(self, processo):
        word_app, doc = self._aguarda_word_com_airr(processo.numero)
        if not doc:
            self._log(f'[word] timeout — Word não abriu documento para {processo.numero}', sucesso=False)
            return False

        ic('lanca_DA', doc.Name)

        if doc.ReadOnly:
            self._log(f'[word] FALHA — documento somente leitura: {doc.Name}', sucesso=False)
            doc.Close(SaveChanges=False)
            return False

        word_app.Activate()

        success = self._inserir_no_word(
            word_app,
            doc,
            processo.triagem_mppf.texto_despacho_admissibilidade,
        )

        if not success:
            return False

        # Save em thread separada para escapar do contexto greenlet do Playwright
        self._log(f'[word] salvando resultado no banco para {processo.numero}...')
        resultado = {}

        def _save():
            try:
                processo.triagem_mppf.foi_lancada_DA_no_GE = True
                processo.triagem_mppf.save()
                resultado['ok'] = True
            except Exception as e:
                resultado['erro'] = e

        t = threading.Thread(target=_save)
        t.start()
        t.join()

        if resultado.get('ok'):
            self._log(f'DA lançada: {processo.numero}', sucesso=True)
            return processo.numero

        self._log(f'[word] ERRO ao salvar no banco: {resultado.get("erro")}', sucesso=False)
        return False
