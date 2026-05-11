import re
from pathlib import Path
from docx import Document
from processos.models import Responsavel

class DocxService:
    def __init__(self):
        # Carregamos as siglas do banco de dados para memória para performance
        # Criamos um dicionário: {'SIGLA': objeto_responsavel}
        self.responsaveis_dict = {
            r.inicial.upper(): r for r in Responsavel.objects.all() if r.inicial
        }

    def extrair_sigla_valida(self, texto):
        """Extrai a última sigla válida de uma linha tipo GMKA/AS/BS/RM"""
        texto_upper = texto.upper()
        # Limpeza: mantém apenas letras e barras
        texto_limpo = re.sub(r'[^A-Z/]', '', texto_upper)
        
        # Regex para identificar o padrão do tribunal
        padrao_sigla = re.compile(r"^(GMKA/|KA/)([A-Z/]*)")
        match = padrao_sigla.match(texto_limpo)

        if not match:
            return None

        siglas_texto = match.group(2)
        siglas_brutas = siglas_texto.split('/')
        
        # Busca a última sigla válida (de trás para frente)
        for s in reversed(siglas_brutas):
            s_limpa = s.strip()
            # Ignora siglas de controle que não são minutantes
            if s_limpa and s_limpa not in ("RM", "MPPF", "GMKA", "KA"):
                if s_limpa in self.responsaveis_dict:
                    return self.responsaveis_dict[s_limpa]
        return None

    def analisar_minutante_no_arquivo(self, caminho_arquivo):
        """Lê o docx e retorna o objeto Responsavel encontrado"""
        try:
            doc = Document(caminho_arquivo)
            for p in doc.paragraphs:
                texto = p.text.strip()
                # Normaliza para verificar início da linha
                texto_norm = re.sub(r'\s+', '', texto).upper()
                
                if texto_norm.startswith(("GMKA/", "KA/")):
                    return self.extrair_sigla_valida(texto)
        except Exception as e:
            print(f"Erro ao ler {caminho_arquivo}: {e}")
        return None