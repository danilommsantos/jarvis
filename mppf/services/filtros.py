from datetime import datetime, time as dt_time, timedelta
from django.db.models import Count, Q, Case, When, Value, IntegerField, Max, F
from django.db.models.functions import Coalesce
from django.utils import timezone
from mppf.models import TriagemMPPF
from pathlib import Path
from processos.models import Processo, Peca

def incluir_triagem():
    return Processo.objects.filter(
        classe__nome='AIRR',
        responsavel__nome_completo='Danilo Monteiro De Melo Santos',
        movimentacao_interna__nome='(GE) Triagem Geral',
        triagem_mppf__isnull=True,
        impedido=False,
    ).annotate(
        qtd_recursos=Count('partes_autoras') # <-- Atributo padronizado
    ).order_by('qtd_recursos')
    
    

def triagem():
    return Processo.objects.filter(
        classe__nome='AIRR',
        responsavel__nome_completo='Danilo Monteiro De Melo Santos',
        movimentacao_interna__nome='(GE) Triagem Geral',
        esta_no_acervo=True,
        triagem_mppf__isnull=False,        
        impedido=False,
    ).annotate(
        qtd_recursos=Coalesce(F('triagem_mppf__quantidade_de_recursos'), Value(1))
    )


def triar():
    return triagem().filter(triagem_mppf__resultado__isnull=True)


def triar_com_pdf(pasta = Path(r"D:/Processos")):
    pdfs = [arquivo.stem for arquivo in pasta.glob("*.pdf")]    
    return triar().filter(numero__in=pdfs)


def triados():
    return triagem().filter(
        triagem_mppf__resultado__isnull=False,
        )


def triados_sem_minuta():
    return triados().filter(
        triagem_mppf__foi_criada_minuta_GE=False,
        )


def triados_com_minuta():
    return triados().filter(        
        triagem_mppf__foi_criada_minuta_GE=True,
    )


def criada_minuta_GE():
    return triados_com_minuta().filter(
        triagem_mppf__foi_lancada_DA_no_GE=False,
        triagem_mppf__foi_enviado_para_assinatura=False,
    ).order_by('triagem_mppf__quantidade_de_recursos')


def lancada_DA_no_GE():
    return triados_com_minuta().filter(
        triagem_mppf__foi_lancada_DA_no_GE=True,
        triagem_mppf__foi_enviado_para_assinatura=False,
    ).order_by('triagem_mppf__quantidade_de_recursos')


def codigo_235():
    return lancada_DA_no_GE().filter(
        triagem_mppf__resultado__slug='fazer-mppf-in40',
    )


def codigo_239():
    return lancada_DA_no_GE().filter(
        triagem_mppf__resultado__slug='fazer-mppf',
    )


def codigo_242():
    return lancada_DA_no_GE().filter(
        triagem_mppf__resultado__slug='fazer-mppf-misto',
    )


def enviado_para_assinatura():
    return triados_com_minuta().filter(
        triagem_mppf__foi_enviado_para_assinatura=True,
    ).order_by('triagem_mppf__quantidade_de_recursos')


def proximo_triar():
    return triar_com_pdf().filter(
        triagem_mppf__resultado__isnull=True,
    ).order_by('triagem_mppf__qtd_recursos', 'triagem_mppf__paginas').first()
    


# Filtros de produtividade

def produtividade_geral():
    return Processo.objects.filter(
        classe__nome='AIRR',
        triagem_mppf__isnull=False,        
    )

 
def produtividade_feitos():
    return produtividade_geral().filter(
        triagem_mppf__resultado__isnull=False,       
    ) 
 
    
def produtividade_aproveitados():
    return produtividade_geral().filter(
        triagem_mppf__resultado__slug__in=['fazer-mppf', 'fazer-mppf-in40', 'fazer-mppf-misto']
        )


def produtividade_geral_acervo():
    return produtividade_geral().filter(
        esta_no_acervo=True,
        responsavel__nome_completo='Danilo Monteiro De Melo Santos',
        movimentacao_interna__nome='(GE) Triagem Geral',
    )
    
 
def produtividade_feitos_acervo():
    return produtividade_geral_acervo().filter(
        triagem_mppf__resultado__isnull=False,       
    ) 
 
    
def produtividade_aproveitados_acervo():
    return produtividade_geral_acervo().filter(
        triagem_mppf__resultado__slug__in=['fazer-mppf', 'fazer-mppf-in40', 'fazer-mppf-misto']
        )