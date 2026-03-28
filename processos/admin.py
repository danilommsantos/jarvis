from django.contrib import admin
from .models import Processo, Advogado, Parte, OrgaoJulgador, Classe, Assunto

@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = ('fase_completa', 'numero', 'data_entrada', 'responsavel')
    search_fields = ('numero', 'fase_completa')
    list_filter = ('fase_completa', 'responsavel', 'data_entrada')

# Registra os outros de forma simples
admin.site.register(Advogado)
admin.site.register(Parte)
admin.site.register(OrgaoJulgador)
admin.site.register(Classe)
admin.site.register(Assunto)
