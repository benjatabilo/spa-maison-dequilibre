from django.urls import path
from adminApp import view

urlpatterns = [
    path('', view.panel, name='panel_admin'),
    path('turnos/', view.turnos, name='turnos_admin'),
    path('clientes/', view.clientes, name='clientes_admin'),
    path('perfil/', view.mi_perfil, name='perfil_admin'),
]