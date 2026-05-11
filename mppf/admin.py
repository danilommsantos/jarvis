from django.contrib import admin
from .models import Materia, ExpressaoMateria, TriagemMPPF, ResultadoTriagem, TriagemMateria, ExpressaoMarcador


class TriagemMateriaInline(admin.TabularInline):
    model = TriagemMateria
    extra = 1  # Número de linhas vazias para nova inserção
    autocomplete_fields = ['materia'] # Recomendado se tiver muitas matérias


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'get_data_referencia', 'get_solucoes_compativeis', 'descricao')
    def get_data_referencia(self, obj):
        if obj.data_referencia:
            return obj.data_referencia.strftime('%d.%m.%Y')
        return "-" # Retorno seguro caso a data esteja vazia (null)
    def get_solucoes_compativeis(self, obj):
        return ", ".join([solucao.nome for solucao in obj.solucoes_compativeis.all()])
    get_data_referencia.short_description = 'Data de Referência'
    get_solucoes_compativeis.short_description = 'Soluções Permitidas'
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('solucoes_compativeis')
    list_editable = ('descricao',)
    list_filter = ('ativa', 'data_referencia')
    search_fields = ('nome',)
    ordering = ('nome',)


@admin.register(ExpressaoMateria)
class ExpressaoMateriaAdmin(admin.ModelAdmin):
    list_display = ('texto', 'usar_regex', 'materia') 
    list_filter = ('usar_regex', 'materia__nome')
    search_fields = ('materia__nome', 'texto')


@admin.register(ExpressaoMarcador)
class ExpressaoMarcadorAdmin(admin.ModelAdmin):
    list_display = ['texto']
    search_fields = ['texto']


@admin.register(ResultadoTriagem)
class ResultadoTriagemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'cor_classe', 'nivel_prioridade')
    list_editable = ('nivel_prioridade',)
    prepopulated_fields = {"slug": ("nome",)}
    
    
@admin.register(TriagemMPPF)
class TriagemMPPFAdmin(admin.ModelAdmin):
    list_display = ('processo__numero', 'quantidade_de_recursos', 'resultado')
    inlines = [TriagemMateriaInline]
    list_filter = ('foi_criada_minuta_GE', 'foi_lancada_DA_no_GE', 'foi_enviado_para_assinatura', 'foi_conferida_a_quantidade_de_recursos')
    search_fields = ('processo__numero', )
    
    def get_processo_numero(self, obj):
        return obj.processo.numero
    get_processo_numero.short_description = 'Número do Processo'

    fieldsets = (
        ('Identificação', {
            'fields': ('processo', 'quantidade_de_recursos', 'paginas')
        }),
        ('Análise de Matérias', {
            # CORREÇÃO 2: Remova 'materias' da lista de fields aqui
            'fields': (
                'foi_criada_minuta_GE', 
                'foi_lancada_DA_no_GE', 
                'foi_enviado_para_assinatura', 
                'foi_conferida_a_quantidade_de_recursos',
            )
        }),
        ('Resultado e Ações', {
            'fields': ('resultado',)
        }),
        ('Conteúdo', {
            'fields': ('texto_despacho_admissibilidade',),
            'classes': ('collapse',),
        }),
    )