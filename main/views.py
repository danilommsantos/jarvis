from django.shortcuts import render
from processos.models import Processo

def index(request):
    # Estatísticas simples para os cards do Phoenix
    context = {
        'total_processos': Processo.objects.count(),
    }
    return render(request, 'main/index.html', context)