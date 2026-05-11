from datetime import date
from django.db import models, transaction
from django.db.models import Max
from django.db.models.functions import Length
from main.models import BaseModel
from processos.models import Processo
import re


class ExpressaoMarcador(BaseModel):
    texto = models.CharField("Expressão / Fragmento de Texto", max_length=600)
    class Meta:
        verbose_name = "Marcador"
        verbose_name_plural = "Marcadores"
        ordering = ['texto']

    def __str__(self):
        return f"{self.texto}"


class ResultadoTriagem(BaseModel):
    """
    Nova tabela para armazenar os tipos de resultados possíveis.
    Permite expansão futura sem alterações no esquema do banco.
    """
    nome = models.CharField("Nome do Resultado", max_length=100)
    slug = models.SlugField("Identificador (Slug)", max_length=100, unique=True) # Ex: 'fazer', 'fazer_in40'
    cor_classe = models.CharField("Classe CSS/Cor", max_length=50, default="primary")
    ativo = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField("Ordem", null=True, blank=True)
    nivel_prioridade = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Resultado de Triagem"
        verbose_name_plural = "Resultados de Triagem"
        ordering = ['ordem']

    def __str__(self):
       return self.nome
   

class Materia(BaseModel):
    """
    Representa as matérias jurídicas que o sistema deve procurar no DA.
    Ex: 'Intempestividade', 'Deserção', 'Tema X do STF'.
    """
    nome = models.CharField("Nome da Matéria", max_length=200, unique=True)
    descricao = models.TextField("Descrição da Matéria", blank=True, null=True)
    ativa = models.BooleanField("Regra Ativa?", default=True)
    data_referencia = models.DateField("Data de Referência", null=True, blank=True, default=date(1900, 1, 1),)
    solucoes_compativeis = models.ManyToManyField(
        ResultadoTriagem,
        blank=True,
        related_name='materias_que_permitem',
        help_text="Quais soluções ficam habilitadas quando essa matéria aparece?"
    )

    @property
    def leva_a_suspensao(self):
        """
        Retorna True se alguma das soluções compatíveis desta 
        matéria for 'suspender'.
        """
        return self.solucoes_compativeis.filter(slug='suspender').exists()
    
    class Meta:
        verbose_name = "Matéria de Triagem"
        verbose_name_plural = "Matérias de Triagem"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome}"


class ExpressaoMateria(BaseModel):
    """
    Lista de frases, palavras ou fragmentos de texto que denotam 
    a existência de uma matéria no Despacho de Admissibilidade.
    Uma matéria pode ter várias formas de ser escrita.
    """
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='expressoes')
    texto = models.CharField("Expressão / Fragmento de Texto", max_length=600)
    
    # Opcional: Se quiser usar Expressões Regulares (Regex) futuramente
    usar_regex = models.BooleanField("É Expressão Regular (Regex)?", default=False)

    class Meta:
        verbose_name = "Expressão de Matéria"
        verbose_name_plural = "Expressões de Matérias"
        ordering = ['texto']

    def __str__(self):
        return f'"{self.texto}" -> {self.materia.nome}'
    

class TriagemMateria(BaseModel):
    """
    Tabela intermediária que conecta Triagem e Matéria, 
    armazenando metadados sobre essa ligação.
    """
    class Origem(models.TextChoices):
        SISTEMA = 'SISTEMA', 'Identificado pelo Robô'
        HUMANO = 'HUMANO', 'Adicionado Manualmente'

    triagem = models.ForeignKey('TriagemMPPF', on_delete=models.CASCADE)
    materia = models.ForeignKey('Materia', on_delete=models.CASCADE)
    
    origem = models.CharField(
        max_length=10, 
        choices=Origem.choices, 
        default=Origem.HUMANO
    )

    class Meta:
        unique_together = ('triagem', 'materia') # Impede duplicidade
        
               
# ---------------------------------------------------------------------
# ATUALIZAÇÃO DA TABELA DE TRIAGEM
# ---------------------------------------------------------------------
class TriagemMPPF(BaseModel):
    """
    Ficha de triagem do processo atualizada com os novos requisitos.
    """
    processo = models.OneToOneField(Processo, on_delete=models.CASCADE, related_name='triagem_mppf')
    
    texto_despacho_admissibilidade = models.TextField("Texto da DA", blank=True, null=True)
    quantidade_de_recursos = models.PositiveIntegerField("Quantidade de Recursos", null=True, blank=True)    
    paginas = models.FloatField("Páginas Estimadas", default=0)
    materias = models.ManyToManyField(
        Materia, 
        through=TriagemMateria, 
        blank=True, 
        related_name='triagens_onde_aparece'
    )

    # Status / Ações Manuais e Automáticas
    foi_editada_DA = models.BooleanField("Foi Editada DA?", default=False)
    foi_conferida_a_quantidade_de_recursos = models.BooleanField("Foi Conferida Qtd. de Recursos?", default=False)
    foi_criada_minuta_GE = models.BooleanField("Foi criada minuta no GE?", default=False)
    foi_lancada_DA_no_GE = models.BooleanField("Foi lançada DA no GE?", default=False)
    foi_enviado_para_assinatura = models.BooleanField("Foi enviado para assinatura?", default=False)
    
    resultado = models.ForeignKey(
        ResultadoTriagem, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='resultados_triagem'
    )
    
    @property
    def quantidade_de_recursos_calculada(self):
        total = 0 if self.texto_despacho_admissibilidade is None else self.texto_despacho_admissibilidade.lower().count('recurso de:')
        return 1 if total == 0 else total

    def atualizar_paginas(self):        
        self.paginas = round(len(self.texto_despacho_admissibilidade) / 2000, 1)
    
    def conferir_materias_no_texto(self):
        """
        Remove matérias identificadas anteriormente pelo sistema e 
        realiza uma nova varredura, preservando as inserções manuais.
        """
        if not self.texto_despacho_admissibilidade:
            # Se o texto sumiu, limpamos apenas o que o sistema sugeriu
            self.triagemmateria_set.filter(origem='SISTEMA').delete()
            return

        # ========================================================
        # LIMPEZA SELETIVA:
        # Apagamos apenas os vínculos criados pelo robô.
        # As linhas com origem='HUMANO' permanecem intactas.
        # ========================================================
        self.triagemmateria_set.filter(origem='SISTEMA').delete()
        
        texto_original = self.texto_despacho_admissibilidade
        texto_lower = texto_original.lower()
        
        expressoes = (
            ExpressaoMateria.objects
            .filter(materia__ativa=True)
            .select_related('materia')
            .annotate(tamanho=Length('texto'))
            .order_by('-tamanho')
        )
        with transaction.atomic():
            for exp in expressoes:
                achou = False
                if exp.usar_regex:
                    if re.search(exp.texto, texto_original, re.IGNORECASE):
                        achou = True
                else:
                    padrao = rf"\b{re.escape(exp.texto)}\b"
                    if re.search(padrao, texto_original, re.IGNORECASE):
                        achou = True
                
                if achou:
                    # Usamos get_or_create para o caso de o robô encontrar 
                    # algo que o humano já tinha marcado (evita duplicidade)
                    TriagemMateria.objects.get_or_create(
                        triagem=self,
                        materia=exp.materia,
                        defaults={'origem': TriagemMateria.Origem.SISTEMA}
                    )
        self.save()
        
    def get_solucoes_permitidas(self):
        """
        Calcula dinamicamente quais botões devem estar ativos com base na 
        hierarquia de prioridades das matérias identificadas.
        """
        # 1. Busca todas as soluções vinculadas às matérias desta triagem
        solucoes_das_materias = ResultadoTriagem.objects.filter(
            materias_que_permitem__in=self.materias.all(),
            ativo=True
        ).distinct()
        # 2. Se não houver matérias ou soluções vinculadas, retorna o padrão (Nível 1)
        if not solucoes_das_materias.exists():
            return ResultadoTriagem.objects.filter(slug='fazer-mppf', ativo=True)
        # 3. Encontra o nível de prioridade mais alto presente (Ex: 3 ganha de 2)
        nivel_maximo = solucoes_das_materias.aggregate(Max('nivel_prioridade'))['nivel_prioridade__max']
        # 4. Retorna apenas as soluções que pertencem a esse nível máximo
        return solucoes_das_materias.filter(nivel_prioridade=nivel_maximo)
    
    class Meta:
        verbose_name = "Triagem MPPF"
        verbose_name_plural = "Triagens MPPF"
        ordering = ['quantidade_de_recursos', 'paginas']

    def __str__(self):
        return f"Triagem {self.processo.numero}"
        
    def save(self, *args, **kwargs):
        # Calcula a estimativa de páginas antes de salvar
        if self.texto_despacho_admissibilidade:
            caracteres = len(self.texto_despacho_admissibilidade)
            self.paginas_estimadas = round(caracteres / 2000, 1)
        else:
            self.paginas_estimadas = 0       
        super().save(*args, **kwargs)        

