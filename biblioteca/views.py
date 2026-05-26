from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone

from .models import Categoria, Documento
from .forms import DocumentoForm


def dashboard(request):
    categorias = list(Categoria.objects.order_by('nome'))
    total = Documento.objects.count()
    lidos = Documento.objects.filter(lido=True).count()
    pendentes_count = total - lidos
    pct = round(lidos / total * 100, 1) if total else 0

    cat_stats = []
    for cat in categorias:
        docs = list(cat.documentos.all())
        t = len(docs)
        if not t:
            continue
        l = sum(1 for d in docs if d.lido)
        cat_stats.append({
            'categoria': cat,
            'total': t,
            'lidos': l,
            'pct': round(l / t * 100),
        })

    proximos = (
        Documento.objects
        .filter(lido=False)
        .select_related('categoria')
        .order_by('-prioridade', 'categoria__nome', 'ordem')[:10]
    )

    return render(request, 'biblioteca/dashboard.html', {
        'total': total,
        'lidos': lidos,
        'pendentes_count': pendentes_count,
        'pct': pct,
        'cat_stats': cat_stats,
        'proximos': proximos,
        'categorias': categorias,
    })


def documento_list(request):
    categorias = list(Categoria.objects.order_by('nome'))
    qs = Documento.objects.select_related('categoria').order_by('categoria__nome', 'ordem')

    cat_slug = request.GET.get('categoria', '')
    status = request.GET.get('status', '')

    if cat_slug:
        qs = qs.filter(categoria__slug=cat_slug)
    if status == 'lido':
        qs = qs.filter(lido=True)
    elif status == 'pendente':
        qs = qs.filter(lido=False)

    return render(request, 'biblioteca/documentos.html', {
        'documentos': qs,
        'categorias': categorias,
        'cat_slug': cat_slug,
        'status': status,
    })


def documento_detalhe(request, slug):
    doc = get_object_or_404(
        Documento.objects.select_related('categoria'), slug=slug
    )
    categorias = list(Categoria.objects.order_by('nome'))
    return render(request, 'biblioteca/detalhe.html', {
        'doc': doc,
        'categorias': categorias,
    })


def documento_novo(request):
    categorias = list(Categoria.objects.order_by('nome'))
    if request.method == 'POST':
        form = DocumentoForm(request.POST)
        if form.is_valid():
            doc = form.save()
            messages.success(request, f'Documento "{doc.titulo}" cadastrado com sucesso.')
            return redirect('biblioteca:detalhe', slug=doc.slug)
    else:
        form = DocumentoForm()
    return render(request, 'biblioteca/form_documento.html', {
        'form': form,
        'categorias': categorias,
        'titulo_pagina': 'Novo Documento',
    })


def documento_editar(request, slug):
    doc = get_object_or_404(Documento, slug=slug)
    categorias = list(Categoria.objects.order_by('nome'))
    if request.method == 'POST':
        form = DocumentoForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, f'Documento "{doc.titulo}" atualizado.')
            return redirect('biblioteca:detalhe', slug=doc.slug)
    else:
        form = DocumentoForm(instance=doc)
    return render(request, 'biblioteca/form_documento.html', {
        'form': form,
        'doc': doc,
        'categorias': categorias,
        'titulo_pagina': f'Editar: {doc.titulo}',
    })


@require_POST
def deploy_cloudflare(request):
    from .services.github_publisher import publicar_documentos
    try:
        resultado = publicar_documentos()
        return JsonResponse({
            'ok': True,
            'publicados': resultado['publicados'],
            'erros': resultado['erros'],
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'erros': str(e)}, status=500)


@require_POST
def marcar_lido(request, slug):
    doc = get_object_or_404(Documento, slug=slug)
    doc.lido = not doc.lido
    doc.data_leitura = timezone.now() if doc.lido else None
    doc.save(update_fields=['lido', 'data_leitura'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'lido': doc.lido,
            'data': doc.data_leitura.isoformat() if doc.data_leitura else None,
        })
    return redirect('biblioteca:detalhe', slug=slug)
