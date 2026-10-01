from django.urls import path
from django.contrib.auth import views as auth_views
from usuarioApp import views

urlpatterns = [
    # Navegación Pública y Consulta
    path('', views.inicio, name='inicio_usuario'),
    path('terapias/', views.terapias, name='terapias'),
    path('terapeutas/', views.terapeutas, name='terapeutas'),

    # Autenticación de Usuarios / Clientes
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('panel/', views.mi_panel, name='mi_panel'),
    path('registro/', views.registro_view, name='registro'),

    # Perfil del Cliente
    path('perfil/', views.mi_perfil, name='mi_perfil'),

    # CRUD de Reservas (Cliente)
    path('reservas/', views.mis_reservas, name='mis_reservas'),
    path('reservas/nueva/', views.crear_reserva, name='crear_reserva'),
    path('reservas/<int:pk>/', views.detalle_reserva, name='detalle_reserva'),
    path('reservas/<int:pk>/editar/', views.editar_reserva, name='editar_reserva'),
    path('reservas/<int:pk>/cancelar/', views.cancelar_reserva, name='cancelar_reserva'),
    path('reservas/<int:pk>/eliminar/', views.eliminar_reserva, name='eliminar_reserva'),

    # Endpoints AJAX para el formulario de reserva (selects dependientes y horario)
    path('reservas/ajax/terapeutas-de-terapia/<int:terapia_id>/',
         views.ajax_terapeutas_de_terapia, name='ajax_terapeutas_de_terapia'),
    path('reservas/ajax/terapias-de-terapeuta/<int:terapeuta_id>/',
         views.ajax_terapias_de_terapeuta, name='ajax_terapias_de_terapeuta'),
    path('reservas/ajax/horas-ocupadas/',
         views.ajax_horas_ocupadas, name='ajax_horas_ocupadas'),
]