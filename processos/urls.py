from django.urls import path
from . import views

# O erro costuma ser aqui: ou falta o sinal de '=', ou os colchetes, ou o nome está errado
urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'),
    path('lista_processos/', views.lista_processos, name='lista_processos'),
    path('processo/<int:pk>/', views.processo_detalhe, name='processo_detalhe'),
    path('atualizar_acervo/', views.atualizar_acervo, name='atualizar_acervo'),
    path('atualizar_json_processos/', views.atualizar_json_processos, name='atualizar_json_processos'),
    path('baixar_texto_DA_AIRRs/', views.baixar_texto_DA_AIRRs, name='baixar_texto_DA_AIRRs'),
    path('processo/<int:pk>/sincronizar/', views.sincronizar_processo, name='sincronizar_processo'),
    path('peca/<int:pk>/baixar_texto/', views.baixar_texto, name='baixar_texto'),
]