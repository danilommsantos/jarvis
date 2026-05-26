from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class Categoria(models.Model):
    nome = models.CharField('Nome', max_length=100)
    slug = models.SlugField('Slug', unique=True, max_length=100)
    descricao = models.TextField('Descrição', blank=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class Documento(models.Model):
    FORMATO_CHOICES = [
        ('md', 'Markdown'),
        ('html', 'HTML'),
    ]

    titulo = models.CharField('Título', max_length=255)
    slug = models.SlugField('Slug', unique=True, max_length=255)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        verbose_name='Categoria',
        related_name='documentos',
    )
    conteudo = models.TextField('Conteúdo')
    formato = models.CharField(
        'Formato',
        max_length=4,
        choices=FORMATO_CHOICES,
        default='md',
    )
    ordem = models.IntegerField('Ordem', default=0)
    prioridade = models.IntegerField(
        'Prioridade',
        default=0,
        help_text='0 = normal, 1 = alta, 2 = urgente',
    )
    data_inclusao = models.DateField(
        'Data de Inclusão',
        default=timezone.localdate,
        help_text='Data usada para ordenar a lista de leitura',
    )
    lido = models.BooleanField('Lido', default=False)
    data_leitura = models.DateTimeField('Data de Leitura', null=True, blank=True)
    publicado_github = models.BooleanField('Publicado no GitHub', default=False)
    github_path = models.CharField('Path no GitHub', max_length=500, blank=True)
    data_criacao = models.DateTimeField('Criado em', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['categoria', 'ordem', 'titulo']

    def __str__(self):
        return f'{self.categoria} — {self.titulo}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.titulo)
        super().save(*args, **kwargs)

    def get_github_path(self):
        return f'docs/{self.categoria.slug}/{self.ordem:02d}-{self.slug}.md'


class SyncLog(models.Model):
    TIPO_CHOICES = [
        ('publicar', 'Publicação no GitHub'),
        ('sincronizar', 'Sincronização de Leituras'),
    ]

    data = models.DateTimeField('Data', auto_now_add=True)
    tipo = models.CharField('Tipo', max_length=15, choices=TIPO_CHOICES)
    documentos_afetados = models.IntegerField('Documentos Afetados', default=0)
    erros = models.TextField('Erros', blank=True)
    detalhes = models.TextField('Detalhes', blank=True)

    class Meta:
        verbose_name = 'Log de Sincronização'
        verbose_name_plural = 'Logs de Sincronização'
        ordering = ['-data']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.data.strftime("%d/%m/%Y %H:%M")}'
