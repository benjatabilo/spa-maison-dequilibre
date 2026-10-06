from django.db.models.deletion import RestrictedError
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from adminApp.models import Terapia

from .permissions import SoloAdminEscribe
from .serializers import TerapiaSerializer


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