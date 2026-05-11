from django.db import models
from django.db.models import Count, F, Window, OuterRef, Subquery, Q

from processos.models import Processo, Responsavel, Parte, Advogado
from main.models import BaseModel

class Pauta(BaseModel):
    titulo = models.CharField(max_length=200, help_text="Ex: Pauta 13 a 22.04.2026 Virtual")
    data_inicio = models.DateField()
    data_final = models.DateField()     
    pasta = models.CharField(max_length=500, blank=True, null=True, help_text="Caminho da pasta com as minutas .docx")
    
    class Meta:
        ordering = ['-data_inicio']

    def __str__(self):
        return self.titulo

class ListaProcessos(BaseModel):
    """
    O objeto para partilhar com os colegas.
    Representa um "lote" de processos que entraram na pauta numa data específica.
    """
    pauta = models.ForeignKey(Pauta, on_delete=models.CASCADE, related_name='listas')
    titulo = models.CharField(max_length=100, help_text="Ex: Lote Inicial (10/04), Lote Complementar (15/04)")
    data_inclusao = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.titulo} ({self.pauta.titulo})"

class StatusRevisao(BaseModel):
    """
    Tabela de domínio para os status e resultados possíveis de uma revisão.
    Permite adicionar novos status dinamicamente e marcar mais de um por revisão.
    """
    nome = models.CharField(max_length=100, unique=True, help_text="Ex: Pendente, Corrigido erro material, Liberada")
    descricao = models.TextField(blank=True, help_text="Explicação opcional sobre quando usar este status")
    ativo = models.BooleanField(default=True, help_text="Desmarque para ocultar este status das novas revisões")
    eh_revisado = models.BooleanField(default=False)

    def __str__(self):
        return self.nome

class RevisaoQuerySet(models.QuerySet):
    def ordenar_pela_prioridade(self):
        # 1. Criamos uma subquery que conta o TOTAL de processos do minutante nesta pauta
        # Isso garante que o número não mude mesmo que filtremos os 'revisados' depois
        total_pauta_subquery = RevisaoProcesso.objects.filter(
            pauta_id=OuterRef('pauta_id'),
            minutante_id=OuterRef('minutante_id'),
            rr_provido=False 
        ).values('minutante_id').annotate(total=Count('id')).values('total')

        return self.filter(
            rr_provido=False
        ).annotate(
            total_estatico=Subquery(total_pauta_subquery)
        ).order_by(
            'pulado',                   
            F('total_estatico').desc(nulls_last=True), # Maior volume total primeiro
            'minutante__nome_completo',             
            'processo__fase_completa',             
            'processo__numero'          
        )

class RevisaoProcesso(BaseModel):
    """
    Guarda o seu TRABALHO e vincula o processo ao lote (lista) em que ele entrou na pauta.
    """
    pauta = models.ForeignKey(Pauta, on_delete=models.CASCADE, related_name='revisoes')
    processo = models.ForeignKey(Processo, on_delete=models.RESTRICT, related_name='revisoes_pauta')
    lista_origem = models.ForeignKey(ListaProcessos, on_delete=models.CASCADE, related_name='processos_revisar', null=True, blank=True)
    
    status = models.ManyToManyField(StatusRevisao, related_name='revisoes', blank=True)
    minutante = models.ForeignKey(Responsavel, on_delete=models.SET_NULL, related_name='revisoes_minutadas', blank=True, null=True)
    pulado = models.BooleanField(default=False)
    rr_provido = models.BooleanField(default=False)
    
    tempo_gasto = models.IntegerField(
        default=0, 
        help_text="Tempo total gasto na revisão (em segundos)"
    )
    
    anotacoes = models.TextField(blank=True, help_text="As suas notas sobre o processo nesta pauta.")
    
    objects = RevisaoQuerySet.as_manager()

    class Meta:
        # Regra: Um processo pode aparecer em várias pautas, mas não se repete na mesma pauta.
        constraints = [
            models.UniqueConstraint(fields=['pauta', 'processo'], name='unique_processo_por_pauta')
        ]

    def __str__(self):
        # Como M2M não pode ser acedido diretamente num print simples sem bater no banco, 
        # simplificamos o texto de retorno.
        return f"Revisão: {self.processo} ({self.pauta})"

class ObservacaoRevisao(BaseModel):
    """
    Permite incluir múltiplas observações e dúvidas específicas para cada revisão de processo.
    """
    revisao = models.ForeignKey(RevisaoProcesso, on_delete=models.CASCADE, related_name='observacoes')
    tema = models.TextField(help_text="Tema ou contexto principal da observação.")
    observacao = models.TextField(help_text="Conteúdo detalhado da observação.")
    duvida = models.BooleanField(default=False, help_text="Marque se isto for uma dúvida pendente.")

    def __str__(self):
        tipo = "DÚVIDA" if self.duvida else "OBS"
        # Mostra o tipo e os primeiros 50 caracteres do tema para facilitar a identificação
        return f"[{tipo}] {self.tema[:50]}"
    
    
class Memorial(BaseModel):
    pauta = models.ForeignKey(Pauta, on_delete=models.CASCADE, related_name='memoriais')
    processo = models.ForeignKey(Processo, on_delete=models.CASCADE, related_name='memoriais')
    partes = models.ManyToManyField(Parte, related_name='memoriais', blank=True)
        
    resumo_memorial = models.TextField(blank=True)
    resumo_proposta_decisao = models.TextField(
        blank=True, 
        help_text="Resumo da proposta de decisão que consta do plenário"
    )
    link_memorial = models.URLField(
        max_length=500, 
        blank=True, 
        null=True, 
        help_text="Link para o memorial no Google Drive"
    )

    def __str__(self):
        return f"Memorial no {self.processo}"
    
    
class AtendimentoAdvogado(BaseModel):
    pauta = models.ForeignKey(Pauta, on_delete=models.CASCADE, related_name='atendimentos')
    processo = models.ForeignKey('processos.Processo', on_delete=models.CASCADE, related_name='atendimentos')
    partes = models.ManyToManyField(Parte, related_name='atendimentos', blank=True)
    advogados = models.ManyToManyField(Advogado, related_name='atendimentos', blank=True)
    
    data_horario = models.DateTimeField(help_text="Data e horário do atendimento")    
    resumo_observacoes = models.TextField(blank=True, help_text="Resumo das observações do advogado")
    resumo_proposta_decisao = models.TextField(
        blank=True, 
        help_text="Resumo da proposta de decisão que consta do plenário"
    )
    link_audio = models.URLField(
        max_length=500, 
        blank=True, 
        null=True, 
        help_text="Link para o audio"
    )
    # Vincula um memorial a este atendimento, se houver
    memorial = models.ForeignKey(
        Memorial, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='atendimentos_vinculados'
    )

    def __str__(self):
        return f"Atendimento em {self.data_horario.strftime('%d/%m/%Y %H:%M')} referente ao processo {self.processo}"