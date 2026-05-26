from django.contrib import admin
from .models import Pauta, ListaProcessos, StatusRevisao, RevisaoProcesso, ObservacaoRevisao, Memorial, AtendimentoAdvogado

@admin.register(Pauta)
class PautaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'data_inicio', 'data_final', 'pasta')
    search_fields = ('titulo',)
    list_filter = ('data_inicio', 'data_final')

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

@admin.register(ListaProcessos)
class ListaProcessosAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'pauta', 'data_inclusao', 'criado_em')
    list_filter = ('pauta', 'data_inclusao')
    search_fields = ('titulo', 'pauta__titulo')

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

@admin.register(StatusRevisao)
class StatusRevisaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo', 'descricao', 'eh_revisado')
    list_filter = ('ativo',)
    search_fields = ('nome',)

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

class ObservacaoRevisaoInline(admin.TabularInline):
    """
    Permite adicionar e editar observações diretamente dentro da página de Revisão do Processo.
    """
    model = ObservacaoRevisao
    extra = 1  # Número de linhas em branco extras a exibir por predefinição
    fields = ('tema', 'observacao', 'duvida')

@admin.register(RevisaoProcesso)
class RevisaoProcessoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'pauta', 'lista_origem', 'get_status')
    list_filter = ('pauta', 'lista_origem', 'status', 'minutante')
    search_fields = ('processo__numero', 'anotacoes')
    filter_horizontal = ('status',) # Melhora a interface para selecionar múltiplos status (ManyToMany)
    inlines = [ObservacaoRevisaoInline]

    def get_status(self, obj):
        """Função auxiliar para exibir os status na listagem (já que é ManyToMany)"""
        return ", ".join([s.nome for s in obj.status.all()])
    get_status.short_description = 'Status'

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

@admin.register(ObservacaoRevisao)
class ObservacaoRevisaoAdmin(admin.ModelAdmin):
    list_display = ('tema', 'revisao', 'duvida', 'criado_em')
    list_filter = ('duvida', 'criado_em')
    search_fields = ('tema', 'observacao', 'revisao__processo__numero')

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }
        

@admin.register(Memorial)
class MemorialAdmin(admin.ModelAdmin):
    # Usamos 'exibir_partes' em vez de 'partes' direto
    list_display = ('processo', 'pauta', 'exibir_partes', 'processo__relator__sigla')
    
    # Filtros na barra lateral direita
    list_filter = ('pauta',)
    
    # Barra de pesquisa superior (Atenção: substitua partes__nome pelo campo real da sua classe Parte)
    search_fields = ('processo__numero', 'partes__nome', 'resumo_memorial')
    
    # Substitui o dropdown pesado por uma busca rápida com lupa
    autocomplete_fields = ['processo', 'pauta', 'partes']

    # Método para exibir os itens do ManyToMany na lista do Admin
    def exibir_partes(self, obj):
        # Substitua 'p.nome' pelo atributo correto (ex: p.nome_completo)
        return ", ".join([p.nome for p in obj.partes.all()])
    exibir_partes.short_description = 'Partes'


@admin.register(AtendimentoAdvogado)
class AtendimentoAdvogadoAdmin(admin.ModelAdmin):
    list_display = ('processo', 'exibir_advogados', 'data_horario', 'pauta', 'exibir_partes')
    
    list_filter = ('pauta', 'data_horario')
    
    search_fields = ('processo__numero', 'advogados__nome', 'partes__nome', 'resumo_observacoes')
    
    autocomplete_fields = ['processo', 'pauta', 'memorial', 'partes', 'advogados']

    def exibir_advogados(self, obj):
        return ", ".join([a.nome for a in obj.advogados.all()])
    exibir_advogados.short_description = 'Advogados'

    def exibir_partes(self, obj):
        return ", ".join([p.nome for p in obj.partes.all()])
    exibir_partes.short_description = 'Partes Representadas'