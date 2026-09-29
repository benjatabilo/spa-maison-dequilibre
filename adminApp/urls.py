from django.urls import path
from adminApp import views

urlpatterns = [
    path('', views.panel, name='panel_admin'),
    path('turnos/', views.turnos, name='turnos_admin'),
    path('clientes/', views.clientes, name='clientes_admin'),
    path('clientes/<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:pk>/estado/', views.cambiar_estado_cliente, name='cambiar_estado_cliente'),
    path('perfil/', views.mi_perfil, name='perfil_admin'),

    # CRUD de Terapias (mantenedor con base de datos)
    path('terapias/', views.lista_terapias, name='lista_terapias'),
    path('terapias/nueva/', views.crear_terapia, name='crear_terapia'),
    path('terapias/<int:pk>/editar/', views.editar_terapia, name='editar_terapia'),
    path('terapias/<int:pk>/eliminar/', views.eliminar_terapia, name='eliminar_terapia'),

    # CRUD de Terapeutas
    path('terapeutas/', views.lista_terapeutas, name='lista_terapeutas'),
    path('terapeutas/nuevo/', views.crear_terapeuta, name='crear_terapeuta'),
    path('terapeutas/<int:pk>/editar/', views.editar_terapeuta, name='editar_terapeuta'),
    path('terapeutas/<int:pk>/eliminar/', views.eliminar_terapeuta, name='eliminar_terapeuta'),
]