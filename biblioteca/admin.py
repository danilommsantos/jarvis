from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Categoria, Documento, SyncLog


# ── Ações em lote ────────────────────────────────────────────────────────────

def publicar_no_github(modeladmin, request, queryset):
    from django.contrib import messages
    from .services import github_publisher

    if not _github_configurado():
        messages.error(request, 'Configure GITHUB_TOKEN e GITHUB_REPO nas variáveis de ambiente.')
        return
    try:
        resultado = github_publisher.publicar_documentos(list(queryset))
        messages.success(request, f'{resultado["publicados"]} documento(s) publicado(s) com sucesso.')
        if resultado.get('erros'):
            messages.warning(request, f'Erros parciais:\n{resultado["erros"]}')
    except Exception as e:
        messages.error(request, f'Erro ao publicar no GitHub: {e}')


publicar_no_github.short_description = 'Publicar selecionados no GitHub'


def sincronizar_status_leitura(modeladmin, request, queryset):
    from django.contrib import messages
    from .services import github_sync

    if not _github_configurado():
        messages.error(request, 'Configure GITHUB_TOKEN e GITHUB_REPO nas variáveis de ambiente.')
        return
    try:
        resultado = github_sync.sincronizar(documentos=list(queryset))
        messages.success(request, f'{resultado["atualizados"]} documento(s) atualizado(s) com status de leitura.')
        if resultado.get('erros'):
            messages.warning(request, f'Erros:\n{resultado["erros"]}')
    except Exception as e:
        messages.error(request, f'Erro ao sincronizar: {e}')


sincronizar_status_leitura.short_description = 'Sincronizar status de leitura do GitHub'


def _github_configurado():
    from django.conf import settings
    return bool(getattr(settings, 'GITHUB_TOKEN', None) and getattr(settings, 'GITHUB_REPO', None))


# ── Categoria ────────────────────────────────────────────────────────────────

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'slug', 'total_documentos', 'progresso_leitura']
    prepopulated_fields = {'slug': ('nome',)}
    search_fields = ['nome', 'descricao']

    @admin.display(description='Total')
    def total_documentos(self, obj):
        return obj.documentos.count()

    @admin.display(description='Progresso')
    def progresso_leitura(self, obj):
        total = obj.documentos.count()
        if not total:
            return '—'
        lidos = obj.documentos.filter(lido=True).count()
        pct = lidos / total * 100
        cor = '#2e7d32' if pct == 100 else ('#f57f17' if pct > 0 else '#999')
        return format_html(
            '<span style="color:{}">{}/{} ({:.0f}%)</span>',
            cor, lidos, total, pct,
        )


# ── Documento ────────────────────────────────────────────────────────────────

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'categoria', 'formato', 'ordem', 'prioridade',
        'lido_badge', 'publicado_badge', 'data_atualizacao',
    ]
    list_filter = ['categoria', 'lido', 'publicado_github', 'prioridade', 'formato']
    search_fields = ['titulo', 'conteudo', 'slug']
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields = [
        'preview_conteudo', 'github_path',
        'data_criacao', 'data_atualizacao', 'data_leitura',
    ]
    actions = [publicar_no_github, sincronizar_status_leitura]
    ordering = ['categoria', 'ordem']
    list_per_page = 50

    fieldsets = (
        ('Identificação', {
            'fields': ('titulo', 'slug', 'categoria', 'formato', 'ordem', 'prioridade'),
        }),
        ('Conteúdo', {
            'fields': ('conteudo', 'preview_conteudo'),
            'classes': ('wide',),
        }),
        ('Status de Publicação', {
            'fields': ('publicado_github', 'github_path'),
        }),
        ('Status de Leitura', {
            'fields': ('lido', 'data_leitura'),
        }),
        ('Metadados', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Lido')
    def lido_badge(self, obj):
        if obj.lido:
            label = f'✓ {obj.data_leitura.strftime("%d/%m/%y") if obj.data_leitura else "Sim"}'
            return format_html('<span style="color:#2e7d32;font-weight:bold">{}</span>', label)
        return format_html('<span style="color:#bbb">—</span>')

    @admin.display(description='GitHub')
    def publicado_badge(self, obj):
        if obj.publicado_github:
            return format_html('<span style="color:#1565c0;font-weight:bold">✓</span>')
        return format_html('<span style="color:#ddd">—</span>')

    @admin.display(description='Preview')
    def preview_conteudo(self, obj):
        if not obj.conteudo:
            return '(sem conteúdo)'
        if obj.formato == 'html':
            return format_html(
                '<div style="border:1px solid #e0e0e0;border-radius:4px;padding:16px;'
                'max-height:500px;overflow-y:auto;background:#fafafa">{}</div>',
                mark_safe(obj.conteudo),
            )
        # Markdown: renderiza com marked.js via CDN
        return format_html(
            '<div id="md-preview-output" style="border:1px solid #e0e0e0;border-radius:4px;'
            'padding:16px;max-height:500px;overflow-y:auto;background:#fafafa;font-family:serif"></div>'
            '<script src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"></script>'
            '<script>'
            '(function(){{'
            '  var ta=document.getElementById("id_conteudo");'
            '  var out=document.getElementById("md-preview-output");'
            '  if(!ta||!out)return;'
            '  function render(){{out.innerHTML=marked.parse(ta.value||"");}} '
            '  ta.addEventListener("input",render);'
            '  render();'
            '}})();'
            '</script>',
        )


# ── SyncLog ──────────────────────────────────────────────────────────────────

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['data', 'tipo', 'documentos_afetados', 'status_erros']
    list_filter = ['tipo']
    readonly_fields = ['data', 'tipo', 'documentos_afetados', 'erros', 'detalhes']

    @admin.display(description='Status')
    def status_erros(self, obj):
        if obj.erros:
            return format_html('<span style="color:#c62828">⚠ Com erros</span>')
        return format_html('<span style="color:#2e7d32">✓ OK</span>')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
