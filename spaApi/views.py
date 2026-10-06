from django.db import transaction
from django.db.models.deletion import RestrictedError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from adminApp.forms import usuario_de_terapeuta
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from usuarioApp.roles import ADMINISTRADOR, obtener_rol

from .permissions import SoloAdminEscribe
from .serializers import TerapeutaAdminSerializer, TerapeutaPublicoSerializer, TerapiaSerializer


@extend_schema(
    summary='¿Quién soy? (endpoint protegido de prueba)',
    responses=inline_serializer('Yo', {'usuario': serializers.CharField()}),
)
@api_view(['GET'])
def yo(request):
    """Endpoint protegido de prueba: dice quién es el usuario del token."""
    return Response({'usuario': request.user.username})


class TerapiaViewSet(viewsets.ModelViewSet):
    """
    Un solo ViewSet entrega: listar y crear (/terapias/) y ver, modificar y borrar (/terapias/<id>/).
    """
    queryset = Terapia.objects.all().order_by('nombre')
    serializer_class = TerapiaSerializer
    permission_classes = [SoloAdminEscribe]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']      # ?search=masaje
    ordering_fields = ['nombre', 'precio']         # ?ordering=-precio

    def destroy(self, request, *args, **kwargs):
        # Reserva usa on_delete=RESTRICT: no se puede borrar una terapia que ya tiene reservas.
        try:
            return super().destroy(request, *args, **kwargs)
        except RestrictedError:
            return Response(
                {'detail': 'No se puede eliminar: la terapia tiene reservas asociadas.'},
                status=status.HTTP_409_CONFLICT,
            )


class TerapeutaViewSet(viewsets.ModelViewSet):
    """
    CRUD de terapeutas. El Administrador ve y escribe todos los campos; Cliente y Terapeuta
    solo consultan, y solo ven los campos públicos (otro serializer).
    """
    queryset = Terapeuta.objects.prefetch_related('terapias').order_by('nombre')
    permission_classes = [SoloAdminEscribe]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'profesion']
    ordering_fields = ['nombre', 'profesion']

    def get_serializer_class(self):
        # swagger_fake_view: cuando se genera la documentación no hay usuario; se muestra el completo
        if getattr(self, 'swagger_fake_view', False) or obtener_rol(self.request.user) == ADMINISTRADOR:
            return TerapeutaAdminSerializer
        return TerapeutaPublicoSerializer

    def destroy(self, request, *args, **kwargs):
        terapeuta = self.get_object()
        cuenta = usuario_de_terapeuta(terapeuta.correo)
        try:
            with transaction.atomic():             # o se borra todo o no se borra nada
                terapeuta.delete()
                if cuenta:
                    cuenta.delete()                # también se borra su cuenta de acceso, igual que en la web
        except RestrictedError:
            return Response(
                {'detail': 'No se puede eliminar: el terapeuta tiene reservas asociadas.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)