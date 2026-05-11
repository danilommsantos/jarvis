from django.urls import path
from . import views

app_name = 'mppf'

urlpatterns = [
    path('kanban/', views.kanban_triagem, name='kanban_triagem'),
    path('criar_triagem_MPPF/', views.criar_triagem_MPPF, name='criar_triagem_MPPF'),
    path('proximo/', views.proximo_triagem, name='proximo_triagem'),
    path('triar/<int:pk>/', views.realizar_triagem, name='realizar_triagem'),
    path('lancar_fluxo_lote/', views.lancar_fluxo_lote, name='lancar_fluxo_lote'),
    path('lanca_DA_no_GE_semiauto/', views.lanca_DA_no_GE_semiauto, name='lanca_DA_no_GE_semiauto'),
    path('relatorios/nao-fazer/', views.relatorio_nao_fazer, name='relatorio_nao_fazer'),
    path('relatorios/aguardando-triagem/', views.relatorio_aguardando_triagem, name='relatorio_aguardando_triagem'),
]