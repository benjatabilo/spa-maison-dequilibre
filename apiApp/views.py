from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from usuarioApp.models import Reserva
from usuarioApp.roles import ADMINISTRADOR, TERAPEUTA, obtener_rol

from .permissions import PermisoReservas, SoloAdminEscribe
from .serializers import (
    PerfilTokenSerializer, ReservaAdminSerializer, ReservaSerializer,
    TerapeutaAdminSerializer, TerapeutaPublicoSerializer, TerapiaSerializer,
    TokenConRolSerializer,
)

# --- Vistas de Autenticación (Mantener igual) ---

@extend_schema(
    tags=['Autenticación'],
    summary='Obtener tokens JWT (login)',
    description=(
        'Entrega un **access token** (corta duración, se envía en cada petición) y un '
        '**refresh token** (larga duración, solo sirve para pedir un nuevo access).\n\n'
        'Uso: `Authorization: Bearer <access>`. Límite de intentos por minuto para frenar '
        'ataques de fuerza bruta.'
    ),
    examples=[
        OpenApiExample(
            'Credenciales',
            value={'username': 'cliente1', 'password': 'MiClave#2026'},
            request_only=True,
        ),
        OpenApiExample(
            'Respuesta exitosa',
            value={
                'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                'rol': 'Cliente',
            },
            response_only=True,
            status_codes=['200'],
        ),
    ],
)
class TokenObtenerView(TokenObtainPairView):
    serializer_class = TokenConRolSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'token'


@extend_schema(
    tags=['Autenticación'],
    summary='Renovar el access token',
    description=(
        'Recibe un **refresh token** válido y entrega un nuevo access token. El refresh token '
        'se rota: el anterior queda invalidado (lista negra) y se devuelve uno nuevo.'
    ),
)
class TokenRenovarView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'token'


@extend_schema(
    tags=['Autenticación'],
    summary='¿Quién soy? (endpoint protegido de prueba)',
    description='Devuelve el usuario y rol asociados al access token enviado. Requiere autenticación.',
    responses={200: PerfilTokenSerializer},
)
@api_view(['GET'])
def yo(request):
    datos = {
        'username': request.user.get_username(),
        'nombre': request.user.get_full_name(),
        'rol': obtener_rol(request.user),
    }
    return Response(PerfilTokenSerializer(datos).data)


# --- Mantenedores y Transacción de Negocio ---

@extend_schema_view(
    list=extend_schema(summary='Listar terapias', description='Cualquier usuario autenticado. Admite `?search=` y `?ordering=precio`.'),
    retrieve=extend_schema(summary='Detalle de una terapia'),
    create=extend_schema(summary='Crear terapia (solo Administrador)'),
    update=extend_schema(summary='Reemplazar una terapia (solo Administrador)'),
    partial_update=extend_schema(summary='Modificar parcialmente una terapia (solo Administrador)'),
    destroy=extend_schema(summary='Eliminar terapia (solo Administrador)',
                          description='Responde 409 si la terapia tiene reservas asociadas.'),
)
@extend_schema(tags=['Mantenedor 1 - Terapias'])
class TerapiaViewSet(viewsets.ModelViewSet):
    queryset = Terapia.objects.all().order_by('nombre')
    serializer_class = TerapiaSerializer
    permission_classes = [SoloAdminEscribe]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'precio']


@extend_schema_view(
    list=extend_schema(summary='Listar terapeutas',
                       description='El Administrador ve todos los campos; Cliente y Terapeuta solo los públicos '
                                   '(sin correo ni certificado).'),
    retrieve=extend_schema(summary='Detalle de un terapeuta'),
    create=extend_schema(summary='Crear terapeuta y su cuenta de acceso (solo Administrador)'),
    update=extend_schema(summary='Reemplazar un terapeuta (solo Administrador)'),
    partial_update=extend_schema(summary='Modificar parcialmente un terapeuta (solo Administrador)'),
    destroy=extend_schema(summary='Eliminar terapeuta (solo Administrador)',
                          description='Responde 409 si el terapeuta tiene reservas asociadas.'),
)
@extend_schema(tags=['Mantenedor 2 - Terapeutas'])
class TerapeutaViewSet(viewsets.ModelViewSet):
    queryset = Terapeuta.objects.prefetch_related('terapias').order_by('nombre')
    permission_classes = [SoloAdminEscribe]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'profesion']
    ordering_fields = ['nombre', 'profesion']

    def get_serializer_class(self):
        # Serializers diferenciados: el campo sensible solo existe en el del Administrador.
        if obtener_rol(self.request.user) == ADMINISTRADOR:
            return TerapeutaAdminSerializer
        return TerapeutaPublicoSerializer

    def perform_destroy(self, instance):
        from django.db import transaction
        from adminApp.forms import usuario_de_terapeuta
        usuario = usuario_de_terapeuta(instance.correo)
        with transaction.atomic():
            instance.delete()          # puede lanzar RestrictedError -> 409 (ver exceptions.py)
            if usuario:
                usuario.delete()       # también se elimina su cuenta de acceso, igual que en la web


@extend_schema_view(
    list=extend_schema(summary='Listar reservas',
                       description='Administrador: todas. Terapeuta: las que le asignaron. Cliente: solo las suyas. '
                                   'Filtros: `?estado=PENDIENTE`, `?fecha=2026-10-20`.'),
    retrieve=extend_schema(summary='Detalle de una reserva'),
    create=extend_schema(summary='Registrar una reserva',
                         description='El cliente queda tomado del token y el estado inicial es PENDIENTE.'),
    update=extend_schema(summary='Reemplazar una reserva'),
    partial_update=extend_schema(summary='Modificar parcialmente una reserva'),
    destroy=extend_schema(summary='Eliminar una reserva'),
)
@extend_schema(tags=['Transacción - Reservas'])
class ReservaViewSet(viewsets.ModelViewSet):
    permission_classes = [PermisoReservas]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha', 'hora', 'estado']

    def get_queryset(self):
        # Control de acceso a nivel de FILA: cada perfil solo "ve" lo que le corresponde.
        # Si pide una reserva ajena, no existe para él -> 404 (no revela que existe).
        if getattr(self, 'swagger_fake_view', False):   # generación del esquema OpenAPI
            return Reserva.objects.none()
        usuario = self.request.user
        rol = obtener_rol(usuario)
        qs = Reserva.objects.select_related('usuario', 'terapia', 'terapeuta')
        if rol == ADMINISTRADOR:
            pass
        elif rol == TERAPEUTA:
            qs = qs.filter(terapeuta__correo__iexact=usuario.email)
        else:
            qs = qs.filter(usuario=usuario)

        estado = self.request.query_params.get('estado')
        fecha = self.request.query_params.get('fecha')
        if estado:
            qs = qs.filter(estado=estado.upper())
        if fecha:
            qs = qs.filter(fecha=fecha)
        return qs

    def get_serializer_class(self):
        if obtener_rol(self.request.user) == ADMINISTRADOR:
            return ReservaAdminSerializer
        return ReservaSerializer

    def perform_create(self, serializer):
        if obtener_rol(self.request.user) == ADMINISTRADOR:
            serializer.save()
        else:
            serializer.save(usuario=self.request.user, estado='PENDIENTE')
