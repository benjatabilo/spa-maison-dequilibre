from django.urls import path
from terapeutaApp import view

urlpatterns = [
    path('', view.rendimiento, name='rendimiento_terapeuta'),
    path('perfil/', view.perfil_inventario, name='perfil_terapeuta'),
]