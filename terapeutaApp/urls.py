from django.urls import path
from terapeutaApp import views

urlpatterns = [
    path('', views.rendimiento, name='rendimiento_terapeuta'),
    path('perfil/', views.perfil_inventario, name='perfil_terapeuta'),
]