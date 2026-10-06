from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from . import views

# 1. Crear el router y registrar los mantenedores y la transacción
router = DefaultRouter()
router.register(r'terapias', views.TerapiaViewSet, basename='terapia')
router.register(r'terapeutas', views.TerapeutaViewSet, basename='terapeuta')
router.register(r'reservas', views.ReservaViewSet, basename='reserva')

urlpatterns = [
    # --- Mantenedores y Transacción (Router) ---
    path('', include(router.urls)),

    # --- Autenticación JWT ---
    path('token/', views.TokenObtenerView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.TokenRenovarView.as_view(), name='token_refresh'),
    path('me/', views.yo, name='api_me'),

    # --- Documentación Swagger / OpenAPI ---
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]