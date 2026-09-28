from django.urls import path
from usuarioApp import views

urlpatterns = [
    path('', views.inicio, name='inicio_usuario'),
    path('terapias/', views.terapias, name='terapias'),
    path('terapeutas/', views.terapeutas, name='terapeutas'),
    path('login/', views.login_view, name='login'),
]
