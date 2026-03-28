from django.urls import path
from . import views

# O erro costuma ser aqui: ou falta o sinal de '=', ou os colchetes, ou o nome está errado
urlpatterns = [
    path('dashboard', views.dashboard, name='dashboard'), # ou o nome que você deu para a view
]