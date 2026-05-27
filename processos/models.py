import requests
from bs4 import BeautifulSoup
from datetime import datetime
from django.utils.timezone import make_aware
from django.db import models
from django.db.models import F
from main.models import BaseModel
from django.contrib.auth.models import User
from icecream import ic

class Responsavel(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nome_completo = models.CharField(max_length=255)
    inicial = models.CharField(max_length=4, null=True)
    def __str__(self):
        return self.nome_completo
    class Meta:
        ordering = ["nome_completo"]  


class Advogado(BaseModel):
    nome = models.CharField(max_length=255, unique=True)
    gera_impedimento = models.BooleanField("Gera Impedimento?", default=False)

    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class Parte(BaseModel):
    nome = models.CharField(max_length=500, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class Ministro(BaseModel):
    nome = models.CharField(max_length=500, unique=True)
    sigla = models.CharField(max_length=5, unique=True)    
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class OrgaoJulgador(BaseModel):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class TipoMinuta(BaseModel):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class SituacaoMinuta(BaseModel):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class MovimentacaoInterna(BaseModel):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class Classe(BaseModel):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class Assunto(BaseModel):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome
    class Meta:
        ordering = ["nome"]


class Processo(BaseModel):
    # Identificação (Sua Regra de Unicidade)
    fase_completa = models.CharField(max_length=50)
    numero = models.CharField(max_length=25) # 0000000-00.0000.0.00.0000
    data_entrada = models.DateField(null=True, blank=True)

    # Relações Chave
    responsavel = models.ForeignKey(Responsavel, on_delete=models.SET_NULL, null=True, related_name="meus_processos")
    relator = models.ForeignKey(Ministro, on_delete=models.SET_NULL, null=True, default=1, related_name="relator_em")
    orgao_julgador = models.ForeignKey(OrgaoJulgador, on_delete=models.SET_NULL, null=True, blank=True)
    classe = models.ForeignKey(Classe, on_delete=models.SET_NULL, null=True, blank=True)
    movimentacao_interna = models.ForeignKey(MovimentacaoInterna, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_minuta = models.ForeignKey(TipoMinuta, on_delete=models.SET_NULL, null=True, blank=True)
    situacao_minuta = models.ForeignKey(SituacaoMinuta, on_delete=models.SET_NULL, null=True, blank=True)

    # Relações de Muitos para Muitos (Múltiplos valores por processo)
    advogados = models.ManyToManyField(Advogado, blank=True)
    assuntos = models.ManyToManyField(Assunto, blank=True)
    partes_autoras = models.ManyToManyField(Parte, related_name="processos_autor", blank=True)
    partes_res = models.ManyToManyField(Parte, related_name="processos_reu", blank=True)

    # Campos de Texto Livre
    movimentacoes = models.TextField(blank=True, null=True)
    admissibilidade = models.TextField(blank=True, null=True)
    andamento = models.CharField(max_length=255, blank=True, null=True)
    
    # Observações e Responsável Extraído
    obs = models.TextField("Conteúdo da Observação", blank=True, null=True)
    obs_responsavel = models.ForeignKey(Responsavel, on_delete=models.SET_NULL, null=True)
    
    # Informações de estado
    esta_no_acervo = models.BooleanField(default=False)
    impedido = models.BooleanField("Impedido?", default=False)

    def sincronizar_pecas(self):
        """
        Acessa a API do TST, verifica peças novas filtrando por tipos específicos
        e faz o download do texto caso seja em formato HTML.
        """
        from .models import Peca, TipoPeca 
        import requests
        from bs4 import BeautifulSoup
        from datetime import datetime
        from django.utils.timezone import make_aware
        # Se estiver usando a biblioteca icecream, mantenha o import. Caso contrário, pode remover os ic()
        # from icecream import ic 

        # Lista de tipos permitidos conforme sua solicitação
        TIPOS_PERMITIDOS = [
            "Decisão do TST",
            "Recurso Extraordinário",
            "Acórdão do TST",
            "Embargos Declaratórios",
            "Contrarrazões",
            "Agravo de Instrumento em Recurso de Revista",
            "Despacho de Admissibilidade do TRT",
            "Recurso de Revista",
            "Acórdão do TRT"
        ]
        
        url = f"http://pecas.ml-prd.rede.tst/api/v1/processos/{self.numero}/pecas"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Se for usar a automação de cookies do navegador que discutimos antes:
        # import browser_cookie3
        # cookies_navegador = browser_cookie3.vivaldi(domain_name='tst.jus.br')
        
        try:
            response = requests.get(url, headers=headers, timeout=15) # Adicione cookies=cookies_navegador se necessário
            
            try:
                dados = response.json()
            except ValueError:
                resposta_crua = response.text[:200] 
                return False, f"A API não retornou dados válidos. Resposta do servidor: {resposta_crua}"
            
            pecas_json = dados.get('pecas', [])
            pecas_adicionadas = 0

            for p_data in pecas_json:
                nome_peca_api = p_data.get('nomeTipoPeca')
                cod_peca = p_data['codPeca']

                # --- FILTRO DE TIPO ---
                if nome_peca_api not in TIPOS_PERMITIDOS:
                    continue # Pula para a próxima peça se não for um dos tipos que você quer

                # VERIFICAÇÃO INCREMENTAL
                if self.pecas.filter(cod_peca=cod_peca).exists():
                    continue
                
                # 1. Garante que o Tipo da Peça existe
                tipo_peca, _ = TipoPeca.objects.get_or_create(
                    sigla=p_data['tipoPeca'],
                    defaults={'nome': nome_peca_api}
                )
                
                # 2. Trata a Data
                data_pub = make_aware(datetime.fromisoformat(p_data['dataPublicacao']))
                
                # 3. Prepara variáveis
                formato = p_data['formatoOriginal']
                url_download = p_data['downloadUrl']
                texto_extraido = ""

                # 4. EXTRAÇÃO DO TEXTO (Se for HTML)
                if formato == "text/html":
                    try:
                        resp_html = requests.get(url_download, headers=headers, timeout=15)
                        if resp_html.status_code == 200:
                            soup = BeautifulSoup(resp_html.content, 'html.parser')
                            texto_extraido = soup.get_text(separator='\n', strip=True) 
                    except Exception as e:
                        print(f"Erro ao baixar HTML da peça {cod_peca}: {e}")

                # 5. Salva a nova Peça
                Peca.objects.create(
                    processo=self,
                    cod_peca=cod_peca,
                    tipo_peca=tipo_peca,
                    data_publicacao=data_pub,
                    formato_original=formato,
                    download_url=url_download,
                    conteudo_texto=texto_extraido
                )
                pecas_adicionadas += 1
            
            self.save()
            return True, f"{pecas_adicionadas} novas peças sincronizadas."
            
        except Exception as e:
            return False, f"Erro ao sincronizar processo {self.numero}: {str(e)}"
    
    class Meta:
        ordering = [F('data_entrada').desc(nulls_first=True)]
        unique_together = ('numero', 'data_entrada')

    def __str__(self):
        return f"{self.fase_completa} - {self.numero}"
    
    
class TipoPeca(BaseModel):
    sigla = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.sigla} - {self.nome}"

    class Meta:
        ordering = ["nome"]


class Peca(BaseModel):
    # Relacionamento com o Processo
    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name="pecas")
    
    # Dados vindos da API
    cod_peca = models.BigIntegerField(unique=True) # Usamos BigInteger pois códigos de tribunais costumam ser grandes
    tipo_peca = models.ForeignKey(TipoPeca, on_delete=models.SET_NULL, null=True, blank=True)
    data_publicacao = models.DateTimeField()
    formato_original = models.CharField(max_length=100)
    download_url = models.URLField(max_length=1000)
    conteudo_texto = models.TextField("Conteúdo da Peça (Texto)", blank=True, null=True)
    
    def baixar_texto(self):
        """
        Faz o download do conteúdo HTML da peça, extrai o texto baseado em
        marcadores específicos e salva no campo conteudo_texto.
        """
        if not self.download_url:
            return False, "Peça sem URL de download."

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            # Acrescenta /html ao final da URL (garantindo que não duplique barras)
            url_html = f"{self.download_url.rstrip('/')}/html"
            ic(url_html)
            
            resp_html = requests.get(url_html, headers=headers, timeout=15)
            
            if resp_html.status_code == 200:
                html_bruto = resp_html.text
                
                marcador_inicio = "<!-- CORPO DO DESPACHO -->"
                marcador_fim = "<!-- Fechamento do despacho -->"
                
                # Lógica de fatiamento com base nos marcadores
                if marcador_inicio in html_bruto and marcador_fim in html_bruto:
                    html_alvo = html_bruto.split(marcador_inicio)[1].split(marcador_fim)[0]
                
                elif marcador_inicio in html_bruto:
                    html_alvo = html_bruto.split(marcador_inicio)[1]
                
                else:
                    html_alvo = html_bruto

                # Limpa as tags HTML do trecho extraído
                soup = BeautifulSoup(html_alvo, 'html.parser')
                self.conteudo_texto = soup.get_text(separator='\n', strip=True) 
                
                # Salva a alteração apenas neste campo para otimizar a query
                self.save(update_fields=['conteudo_texto'])
                
                return True, "Texto extraído e salvo com sucesso."
            
            else:
                return False, f"Falha no download. Código HTTP: {resp_html.status_code}"
                
        except Exception as e:
            return False, f"Erro ao baixar HTML da peça {self.cod_peca}: {str(e)}"

    def __str__(self):
        nome_tipo = self.tipo_peca.nome if self.tipo_peca else "Peça Desconhecida"
        return f"{nome_tipo} ({self.data_publicacao.strftime('%d/%m/%Y')}) - {self.processo.numero}"

    class Meta:
        # Ordenar da peça mais recente para a mais antiga
        ordering = ["-data_publicacao"]