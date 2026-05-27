from django.shortcuts import render
from django.db.models import Q
from processos.models import Processo
from pautas.models import Pauta
from biblioteca.models import Documento
from mppf.models import TriagemMPPF


def index(request):
    context = {
        'total_processos': Processo.objects.count(),
        'total_no_acervo': Processo.objects.filter(esta_no_acervo=True).count()
    }
    return render(request, 'main/index.html', context)


def busca(request):
    q = request.GET.get('q', '').strip()

    processos = Processo.objects.none()
    pautas = Pauta.objects.none()
    documentos = Documento.objects.none()
    triagens = TriagemMPPF.objects.none()

    if q:
        processos = (
            Processo.objects.filter(
                Q(numero__icontains=q)
                | Q(fase_completa__icontains=q)
                | Q(partes_autoras__nome__icontains=q)
                | Q(partes_res__nome__icontains=q)
                | Q(advogados__nome__icontains=q)
            )
            .select_related('responsavel', 'relator', 'classe')
            .distinct()
        )

        pautas = Pauta.objects.filter(titulo__icontains=q).order_by('-data_inicio')

        documentos = (
            Documento.objects.filter(
                Q(titulo__icontains=q) | Q(conteudo__icontains=q)
            )
            .select_related('categoria')
            .distinct()
        )

        triagens = (
            TriagemMPPF.objects.filter(
                Q(processo__numero__icontains=q)
                | Q(processo__fase_completa__icontains=q)
            )
            .select_related('processo', 'resultado', 'processo__responsavel')
            .distinct()
        )

    total = processos.count() + pautas.count() + documentos.count() + triagens.count()

    return render(request, 'main/busca.html', {
        'q': q,
        'processos': processos,
        'pautas': pautas,
        'documentos': documentos,
        'triagens': triagens,
        'total': total,
    })