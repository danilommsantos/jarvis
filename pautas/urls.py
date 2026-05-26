from django.urls import path
from . import views

app_name = 'pautas'

urlpatterns = [
    path('lista_pautas/', views.lista_pautas, name='lista_pautas'),
    path('<int:pk>/', views.pauta, name='pauta'),
    path('revisar_processo/<int:pk>/', views.revisar_processo, name='revisar_processo'),
    path('pauta/<int:pk>/extrair_minutantes_docx/', views.extrair_minutantes_docx, name='extrair_minutantes_docx'),
    path('revisao/<int:pk>/pular/', views.alternar_pular, name='alternar_pular'),
    path('pauta/<int:pauta_pk>/proxima/', views.proxima_revisao, name='proxima_revisao'),
    path('pauta/<int:pk>/relatorio/', views.relatorio_observacoes, name='relatorio_observacoes'),
    path('estatisticas/', views.relatorio_estatisticas, name='relatorio_estatisticas'),
    path('pauta/<int:pk>/estatisticas/', views.relatorio_estatisticas, name='relatorio_estatisticas_pauta'),
    path('qualidade/', views.relatorio_qualidade, name='relatorio_qualidade'),
    path('pauta/<int:pk>/qualidade/', views.relatorio_qualidade, name='relatorio_qualidade_pauta'),
]