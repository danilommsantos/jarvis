from django.db import models
from django.contrib.auth.models import User

class Responsavel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nome_completo = models.CharField(max_length=255)

    def __str__(self):
        return self.nome_completo


class Advogado(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome


class Parte(models.Model):
    nome = models.CharField(max_length=500, unique=True)
    def __str__(self): return self.nome


class OrgaoJulgador(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome


class TipoMinuta(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome


class SituacaoMinuta(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome


class MovimentacaoInterna(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome


class Classe(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome


class Assunto(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    def __str__(self): return self.nome


class Processo(models.Model):
    # Identificação (Sua Regra de Unicidade)
    fase_completa = models.CharField(max_length=50)
    numero = models.CharField(max_length=25) # 0000000-00.0000.0.00.0000
    data_entrada = models.DateField()

    # Relações Chave
    responsavel = models.ForeignKey(Responsavel, on_delete=models.SET_NULL, null=True, related_name="meus_processos")
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

    class Meta:
        unique_together = ('numero', 'data_entrada')

    def __str__(self):
        return f"{self.fase_completa} - {self.numero}"