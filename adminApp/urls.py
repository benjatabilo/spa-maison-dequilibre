from django.urls import path
from adminApp import views

urlpatterns = [
    path('', views.panel, name='panel_admin'),
    path('turnos/', views.turnos, name='turnos_admin'),
    path('clientes/', views.clientes, name='clientes_admin'),
    path('perfil/', views.mi_perfil, name='perfil_admin'),
]