from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Responsavel, Processo, Advogado, Parte, 
    OrgaoJulgador, Classe, Assunto, Peca, TipoPeca, Ministro
)

@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    # Adicionamos 'botao_sincronizar' ao final da lista
    list_display = ('fase_completa', 'numero', 'data_entrada', 'responsavel', 'botao_sincronizar')
    search_fields = ('numero', 'fase_completa')
    list_filter = ('classe', 'responsavel', 'data_entrada')

    def botao_sincronizar(self, obj):
        # Gera a URL para a view de sincronização baseada no ID do processo
        url = reverse('sincronizar_processo', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="background-color: #447e9b; color: white; padding: 2px 8px; border-radius: 4px; text-decoration: none;">Sincronizar</a>',
            url
        )
    
    botao_sincronizar.short_description = 'Ações'

@admin.register(Peca)
class PecaAdmin(admin.ModelAdmin):
    list_display = ('tipo_peca', 'data_publicacao', 'processo', 'formato_original', 'botao_baixar_texto')
    list_filter = ('tipo_peca', 'data_publicacao', 'formato_original')
    search_fields = ('processo__numero', 'conteudo_texto')
    
    # Deixamos o texto extraído e os metadados como apenas leitura para evitar perda de dados
    readonly_fields = ('conteudo_texto', 'cod_peca', 'download_url', 'data_publicacao', 'formato_original')
    
    # Melhora a organização dos campos no formulário de edição/detalhes
    fieldsets = (
        ('Identificação', {
            'fields': ('processo', 'tipo_peca', 'cod_peca')
        }),
        ('Conteúdo Extraído', {
            'fields': ('conteudo_texto',),
        }),
        ('Metadados do Tribunal', {
            'fields': ('data_publicacao', 'formato_original', 'download_url'),
            'classes': ('collapse',), # Deixa essa seção recolhida por padrão
        }),
    )
    
    def botao_baixar_texto(self, obj):
        # Gera a URL para a view de sincronização baseada no ID do processo
        url = reverse('baixar_texto', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="background-color: #447e9b; color: white; padding: 2px 8px; border-radius: 4px; text-decoration: none;">Sincronizar</a>',
            url
        )
    
    botao_baixar_texto.short_description = 'Ações'

@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'user', 'inicial')


@admin.register(Parte)
class ParteAdmin(admin.ModelAdmin):
    search_fields = ['nome'] 

@admin.register(Advogado)
class AdvogadoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'gera_impedimento')
    search_fields = ['nome']
    list_filter = ('gera_impedimento',)


# Registra os modelos auxiliares
admin.site.register(TipoPeca)
admin.site.register(Ministro)
admin.site.register(OrgaoJulgador)
admin.site.register(Classe)
admin.site.register(Assunto)