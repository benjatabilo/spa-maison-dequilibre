from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

# El router genera solo las rutas del CRUD a partir de los ViewSets
router = DefaultRouter()
router.register(r'terapias', views.TerapiaViewSet, basename='terapia')
router.register(r'terapeutas', views.TerapeutaViewSet, basename='terapeuta')
router.register(r'reservas', views.ReservaViewSet, basename='reserva')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', TokenObtainPairView.as_view(), name='token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('yo/', views.yo, name='yo'),

    # Documentación: /api/swagger/ es la página para probar la API con clics
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Cualquier otra URL bajo /api/ -> 404 en JSON (esta línea debe ir SIEMPRE al final)
    re_path(r'^(?P<ruta>.*)$', views.no_encontrado, name='api_no_encontrado'),
]