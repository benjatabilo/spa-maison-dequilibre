from django.db import transaction
from django.db.models.deletion import RestrictedError
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from adminApp.forms import usuario_de_terapeuta
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from usuarioApp.models import Reserva
from usuarioApp.roles import ADMINISTRADOR, TERAPEUTA, obtener_rol

from .exceptions import ConflictoDeEstado
from .permissions import PermisoReservas, SoloAdminEscribe
from .serializers import (
    ReservaAdminSerializer, ReservaSerializer, TerapeutaAdminSerializer,
    TerapeutaPublicoSerializer, TerapiaSerializer,
)

ESTADOS_VALIDOS = [codigo for codigo, _ in Reserva.ESTADOS]


@extend_schema(
    summary='¿Quién soy? (endpoint protegido de prueba)',
    responses=inline_serializer('Yo', {'usuario': serializers.CharField()}),
)
@api_view(['GET'])
def yo(request):
    """Endpoint protegido de prueba: dice quién es el usuario del token."""
    return Response({'usuario': request.user.username})

@extend_schema(exclude=True)          # no aparece en Swagger
@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@authentication_classes([])
@permission_classes([AllowAny])
def no_encontrado(request, ruta=''):
    """Cualquier URL inexistente bajo /api/ responde 404 en JSON (y no con la página HTML de Django)."""
    raise NotFound('El recurso solicitado no existe en esta API.')

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

@extend_schema_view(
    list=extend_schema(parameters=[
        OpenApiParameter('estado', OpenApiTypes.STR, enum=ESTADOS_VALIDOS, description='Filtra por estado.'),
        OpenApiParameter('fecha', OpenApiTypes.DATE, description='Filtra por fecha exacta (AAAA-MM-DD).'),
    ]),
)
class ReservaViewSet(viewsets.ModelViewSet):
    """
    Reservas. Cada perfil ve solo lo suyo: el Administrador todas, el Terapeuta las que le
    asignaron y el Cliente las propias. Las reglas de negocio son las mismas de la aplicación web.
    """
    permission_classes = [PermisoReservas]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha', 'hora', 'estado']

    def _es_admin(self):
        return obtener_rol(self.request.user) == ADMINISTRADOR

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):      # al generar la documentación no hay usuario
            return Reserva.objects.none()
        usuario = self.request.user
        rol = obtener_rol(usuario)
        reservas = Reserva.objects.select_related('usuario', 'terapia', 'terapeuta')

        # Control de acceso por FILA: una reserva ajena "no existe" para quien no es su dueño (404)
        if rol == TERAPEUTA:
            reservas = reservas.filter(terapeuta__correo__iexact=usuario.email) if usuario.email else reservas.none()
        elif rol != ADMINISTRADOR:
            reservas = reservas.filter(usuario=usuario)

        if self.action == 'list':                          # filtros: un valor inválido es error del cliente (400)
            estado = self.request.query_params.get('estado')
            fecha = self.request.query_params.get('fecha')
            if estado:
                if estado.upper() not in ESTADOS_VALIDOS:
                    raise ValidationError({'estado': f'Estado inválido. Usa: {", ".join(ESTADOS_VALIDOS)}.'})
                reservas = reservas.filter(estado=estado.upper())
            if fecha:
                try:
                    fecha_ok = parse_date(fecha)
                except ValueError:                         # formato bien escrito pero fecha imposible (2026-02-30)
                    fecha_ok = None
                if fecha_ok is None:
                    raise ValidationError({'fecha': 'Fecha inválida. Usa el formato AAAA-MM-DD.'})
                reservas = reservas.filter(fecha=fecha_ok)
        return reservas

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False) or self._es_admin():
            return ReservaAdminSerializer
        return ReservaSerializer

    def perform_create(self, serializer):
        if self._es_admin():
            serializer.save()
        else:                                              # el Cliente: dueño = quien llama, estado inicial = PENDIENTE
            serializer.save(usuario=self.request.user, estado='PENDIENTE')

    # --- mismas reglas que la web: una cita cerrada no se toca, y solo se borra lo cancelado ---
    def perform_update(self, serializer):
        if not self._es_admin() and serializer.instance.estado in ('COMPLETADA', 'CANCELADA'):
            raise ConflictoDeEstado('No puedes modificar una reserva cancelada o completada.')
        serializer.save()

    def perform_destroy(self, instance):
        if not self._es_admin() and instance.estado != 'CANCELADA':
            raise ConflictoDeEstado(
                'Solo puedes eliminar reservas ya canceladas. Cancela la reserva primero con '
                'POST /api/reservas/{id}/cancelar/.')
        instance.delete()

    @extend_schema(request=None, responses=ReservaSerializer,
                   summary='Cancelar una reserva (libera el horario)')
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        reserva = self.get_object()                        # una reserva ajena responde 404
        if reserva.estado == 'CANCELADA':
            raise ConflictoDeEstado('La reserva ya está cancelada.')
        if reserva.estado == 'COMPLETADA':
            raise ConflictoDeEstado('No puedes cancelar una reserva completada.')
        reserva.estado = 'CANCELADA'
        reserva.save(update_fields=['estado'])
        return Response(self.get_serializer(reserva).data)