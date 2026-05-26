from django.urls import path
from . import views

app_name = 'biblioteca'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('documentos/', views.documento_list, name='lista'),
    path('documentos/novo/', views.documento_novo, name='novo'),
    path('documentos/<slug:slug>/', views.documento_detalhe, name='detalhe'),
    path('documentos/<slug:slug>/editar/', views.documento_editar, name='editar'),
    path('documentos/<slug:slug>/lido/', views.marcar_lido, name='marcar_lido'),
    path('deploy/', views.deploy_cloudflare, name='deploy'),
]
