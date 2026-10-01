from django.urls import path
from terapeutaApp import views

urlpatterns = [
    path('', views.rendimiento, name='rendimiento_terapeuta'),
    path('reservas/', views.lista_reservas, name='reservas_terapeuta'),
    path('terapias/', views.lista_terapias, name='terapias_terapeuta'),
    path('perfil/', views.perfil_inventario, name='perfil_terapeuta'),
]
