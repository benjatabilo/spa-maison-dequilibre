"""
Documentación de la API (Swagger / OpenAPI).

Este archivo SOLO describe: agrega títulos, ejemplos, parámetros y las respuestas de error
(400, 401, 403, 404, 409) a cada endpoint. No cambia cómo funciona la API. Se carga una vez
desde spaApi/urls.py (la línea "from . import documentacion").
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

from .serializers import (
    ReservaAdminSerializer, ReservaSerializer, TerapeutaAdminSerializer,
    TerapeutaPublicoSerializer, TerapiaSerializer,
)
from .views import ReservaViewSet, TerapeutaViewSet, TerapiaViewSet, TokenObtenerView, TokenRenovarView

# ---------------------------------------------------------------------------------------------
# Respuestas de error reutilizables: todas las de la API tienen la misma forma
# ---------------------------------------------------------------------------------------------
_Detalle = inline_serializer('ErrorDetalle', {'detail': serializers.CharField()})


def _error(descripcion, mensaje):
    return OpenApiResponse(
        response=_Detalle,
        description=descripcion,
        examples=[OpenApiExample('Ejemplo', value={'detail': mensaje}, response_only=True)],
    )


def _error_validacion(ejemplo):
    return OpenApiResponse(
        response=OpenApiTypes.OBJECT,
        description='Datos inválidos. La respuesta indica qué campo falló y por qué.',
        examples=[OpenApiExample('Ejemplo', value=ejemplo, response_only=True)],
    )


E401 = _error('No autenticado: falta el token, es inválido o ya expiró.',
              'Las credenciales de autenticación no se proveyeron.')
E403 = _error('Sin permiso: tu rol no puede realizar esta acción.',
              'No tienes permiso para realizar esta acción.')
E404 = _error('No existe, o no es tuyo (un recurso ajeno responde 404 a propósito).',
              'El recurso solicitado no existe.')
E429 = _error('Demasiadas peticiones: se superó el límite por minuto.',
              'Solicitud limitada. Intenta de nuevo más tarde.')


# ---------------------------------------------------------------------------------------------
# Autenticación (JWT)
# ---------------------------------------------------------------------------------------------
extend_schema_view(
    post=extend_schema(
        tags=['Autenticación'],
        summary='Iniciar sesión (obtener access y refresh)',
        description=(
            'Entrega un **access token** (corta duración, se envía en cada petición como '
            '`Authorization: Bearer <access>`) y un **refresh token** (para pedir un access nuevo). '
            'La respuesta incluye el `rol` del usuario. Máximo 10 intentos por minuto.'
        ),
        examples=[OpenApiExample('Login', value={'username': 'admin', 'password': 'MiClave#2026'},
                                 request_only=True)],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Login correcto.',
                                 examples=[OpenApiExample('Respuesta', response_only=True, value={
                                     'refresh': 'eyJhbGciOiJIUzI1NiIs...',
                                     'access': 'eyJhbGciOiJIUzI1NiIs...',
                                     'rol': 'Administrador'})]),
            401: _error('Usuario o clave incorrectos.',
                        'No se encontró una cuenta activa con las credenciales dadas.'),
            429: E429,
        },
    ),
)(TokenObtenerView)

extend_schema_view(
    post=extend_schema(
        tags=['Autenticación'],
        summary='Renovar el access token (el refresh se usa una sola vez)',
        description=(
            'Cambia un refresh token válido por un access nuevo **y un refresh nuevo**. '
            'El refresh usado queda invalidado (lista negra): reutilizarlo responde 401.'
        ),
        examples=[OpenApiExample('Renovar', value={'refresh': 'eyJhbGciOiJIUzI1NiIs...'},
                                 request_only=True)],
        responses={
            200: OpenApiResponse(response=OpenApiTypes.OBJECT, description='Tokens nuevos.',
                                 examples=[OpenApiExample('Respuesta', response_only=True, value={
                                     'access': 'eyJhbGciOiJIUzI1NiIs...',
                                     'refresh': 'eyJhbGciOiJIUzI1NiIs...'})]),
            401: _error('Refresh inválido, expirado o ya usado.', 'Token is blacklisted'),
            429: E429,
        },
    ),
)(TokenRenovarView)


# ---------------------------------------------------------------------------------------------
# Mantenedor 1: Terapias
# ---------------------------------------------------------------------------------------------
_terapia_ej = {'id': 1, 'nombre': 'Masaje de pies', 'precio': 15000, 'duracion': '30 minutos',
               'descripcion': 'Alivia el cansancio', 'imagen': None}

extend_schema_view(
    list=extend_schema(
        tags=['Terapias'], summary='Listar terapias',
        description='Cualquier usuario autenticado puede consultar. Admite `?search=` (nombre o '
                    'descripción) y `?ordering=` (`nombre`, `precio`; con `-` va al revés).',
        responses={200: TerapiaSerializer(many=True), 401: E401},
    ),
    retrieve=extend_schema(
        tags=['Terapias'], summary='Ver una terapia',
        responses={200: TerapiaSerializer, 401: E401, 404: E404},
    ),
    create=extend_schema(
        tags=['Terapias'], summary='Crear una terapia (solo Administrador)',
        examples=[OpenApiExample('Nueva terapia', request_only=True, value={
            'nombre': 'Masaje de pies', 'precio': 15000, 'duracion': '30 minutos',
            'descripcion': 'Alivia el cansancio'})],
        responses={
            201: TerapiaSerializer,
            400: _error_validacion({'precio': ['El precio debe ser mayor a 0.']}),
            401: E401, 403: E403,
        },
    ),
    update=extend_schema(
        tags=['Terapias'], summary='Modificar una terapia completa (solo Administrador)',
        responses={200: TerapiaSerializer,
                   400: _error_validacion({'nombre': ['Este campo es requerido.']}),
                   401: E401, 403: E403, 404: E404},
    ),
    partial_update=extend_schema(
        tags=['Terapias'], summary='Modificar algunos campos de una terapia (solo Administrador)',
        examples=[OpenApiExample('Cambiar precio', request_only=True, value={'precio': 18000})],
        responses={200: TerapiaSerializer,
                   400: _error_validacion({'precio': ['El precio debe ser mayor a 0.']}),
                   401: E401, 403: E403, 404: E404},
    ),
    destroy=extend_schema(
        tags=['Terapias'], summary='Eliminar una terapia (solo Administrador)',
        description='Si la terapia ya tiene reservas no se puede borrar (409).',
        responses={
            204: OpenApiResponse(description='Eliminada, sin contenido.'),
            401: E401, 403: E403, 404: E404,
            409: _error('La terapia tiene reservas asociadas.',
                        'No se puede eliminar: la terapia tiene reservas asociadas.'),
        },
    ),
)(TerapiaViewSet)


# ---------------------------------------------------------------------------------------------
# Mantenedor 2: Terapeutas (datos sensibles: correo y certificado solo para el Administrador)
# ---------------------------------------------------------------------------------------------
extend_schema_view(
    list=extend_schema(
        tags=['Terapeutas'], summary='Listar terapeutas',
        description='**Administrador:** ve todos los campos (incluye correo y certificado). '
                    '**Cliente y Terapeuta:** solo ven los campos públicos (sin correo ni certificado). '
                    'Admite `?search=` (nombre o profesión) y `?ordering=`.',
        responses={200: TerapeutaAdminSerializer(many=True), 401: E401},
    ),
    retrieve=extend_schema(
        tags=['Terapeutas'], summary='Ver un terapeuta (los campos dependen del rol)',
        responses={200: TerapeutaAdminSerializer, 401: E401, 404: E404},
    ),
    create=extend_schema(
        tags=['Terapeutas'], summary='Crear un terapeuta y su cuenta de acceso (solo Administrador)',
        description='Crea al terapeuta y su usuario para iniciar sesión (con el correo y la `password`). '
                    '`terapias` es la lista de **id** de terapias que realiza (deben existir). '
                    'La `password` solo se envía, nunca se devuelve. `certificado`: PDF o imagen, máx. 5 MB; '
                    '`foto`: imagen, máx. 5 MB. Se revisa el contenido real del archivo, no solo la extensión.',
        examples=[OpenApiExample('Nuevo terapeuta', request_only=True, value={
            'nombre': 'Camila Torres', 'profesion': 'Kinesióloga', 'correo': 'camila.torres@spa.cl',
            'password': 'Clave#Segura2026', 'terapias': [1]})],
        responses={
            201: TerapeutaAdminSerializer,
            400: _error_validacion({'correo': ['Ya existe un terapeuta o usuario con ese correo.'],
                                    'certificado': ['El archivo no es un PDF o imagen válido.']}),
            401: E401, 403: E403,
        },
    ),
    update=extend_schema(
        tags=['Terapeutas'], summary='Modificar un terapeuta completo (solo Administrador)',
        responses={200: TerapeutaAdminSerializer,
                   400: _error_validacion({'correo': ['Ingresa un correo válido.']}),
                   401: E401, 403: E403, 404: E404},
    ),
    partial_update=extend_schema(
        tags=['Terapeutas'], summary='Modificar algunos campos de un terapeuta (solo Administrador)',
        examples=[OpenApiExample('Cambiar profesión', request_only=True, value={'profesion': 'Masoterapeuta'})],
        responses={200: TerapeutaAdminSerializer,
                   400: _error_validacion({'profesion': ['Este campo no puede estar en blanco.']}),
                   401: E401, 403: E403, 404: E404},
    ),
    destroy=extend_schema(
        tags=['Terapeutas'], summary='Eliminar un terapeuta y su cuenta (solo Administrador)',
        description='Si el terapeuta tiene reservas asociadas no se puede borrar (409).',
        responses={
            204: OpenApiResponse(description='Eliminado, sin contenido.'),
            401: E401, 403: E403, 404: E404,
            409: _error('El terapeuta tiene reservas asociadas.',
                        'No se puede eliminar: el terapeuta tiene reservas asociadas.'),
        },
    ),
)(TerapeutaViewSet)


# ---------------------------------------------------------------------------------------------
# Transacción: Reservas
# ---------------------------------------------------------------------------------------------
_reserva_cuerpo = {'terapia': 1, 'terapeuta': 4, 'fecha': '2026-10-20', 'hora': '10:00',
                   'observaciones': 'Prefiero presión suave'}
_E409_ESTADO = _error('La acción choca con el estado actual de la reserva.',
                      'No puedes modificar una reserva cancelada o completada.')

extend_schema_view(
    list=extend_schema(
        tags=['Reservas'], summary='Listar mis reservas',
        description='Cada perfil ve solo lo suyo: el Administrador todas, el Terapeuta las que le asignaron y '
                    'el Cliente las propias. Filtros opcionales: `estado` y `fecha`.',
        parameters=[
            OpenApiParameter('estado', OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                             enum=['PENDIENTE', 'CONFIRMADA', 'COMPLETADA', 'CANCELADA'],
                             description='Filtra por estado.'),
            OpenApiParameter('fecha', OpenApiTypes.DATE, OpenApiParameter.QUERY, required=False,
                             description='Filtra por día (AAAA-MM-DD).'),
        ],
        responses={200: ReservaSerializer(many=True),
                   400: _error_validacion({'fecha': ['Fecha inválida. Usa el formato AAAA-MM-DD.']}),
                   401: E401},
    ),
    retrieve=extend_schema(
        tags=['Reservas'], summary='Ver una reserva',
        responses={200: ReservaSerializer, 401: E401, 404: E404},
    ),
    create=extend_schema(
        tags=['Reservas'], summary='Reservar una hora',
        description='Solo los Clientes (y el Administrador) pueden reservar. El dueño es quien hace la petición y '
                    'el estado inicial es `PENDIENTE`. Reglas: horario 09:00 a 16:00 en horas exactas, el '
                    'terapeuta debe realizar esa terapia, no se puede agendar en el pasado ni en un horario '
                    'ocupado (una reserva cancelada libera el horario).',
        examples=[OpenApiExample('Nueva reserva', request_only=True, value=_reserva_cuerpo)],
        responses={
            201: ReservaSerializer,
            400: _error_validacion({'hora': ['Elige una hora dentro del horario de atención '
                                             '(9:00 a 17:00, en horas exactas).']}),
            401: E401, 403: E403,
        },
    ),
    update=extend_schema(
        tags=['Reservas'], summary='Modificar una reserva completa',
        examples=[OpenApiExample('Reprogramar', request_only=True, value=_reserva_cuerpo)],
        responses={200: ReservaSerializer,
                   400: _error_validacion({'hora': ['Esa hora ya pasó. Elige una hora posterior a la actual.']}),
                   401: E401, 403: E403, 404: E404, 409: _E409_ESTADO},
    ),
    partial_update=extend_schema(
        tags=['Reservas'], summary='Modificar algunos campos de una reserva',
        examples=[OpenApiExample('Cambiar hora', request_only=True, value={'hora': '11:00'})],
        responses={200: ReservaSerializer,
                   400: _error_validacion({'hora': ['Elige una hora dentro del horario de atención '
                                                     '(9:00 a 17:00, en horas exactas).']}),
                   401: E401, 403: E403, 404: E404, 409: _E409_ESTADO},
    ),
    destroy=extend_schema(
        tags=['Reservas'], summary='Eliminar una reserva',
        description='El Cliente solo puede eliminar reservas ya canceladas. El Administrador, cualquiera.',
        responses={
            204: OpenApiResponse(description='Eliminada, sin contenido.'),
            401: E401, 403: E403, 404: E404,
            409: _error('La reserva no está cancelada.',
                        'Solo puedes eliminar reservas ya canceladas. Cancela la reserva primero con '
                        'POST /api/reservas/{id}/cancelar/.'),
        },
    ),
    cancelar=extend_schema(
        tags=['Reservas'], summary='Cancelar una reserva (libera el horario)',
        request=None,
        responses={
            200: ReservaSerializer, 401: E401, 403: E403, 404: E404,
            409: _error('Ya estaba cancelada o ya fue completada.', 'La reserva ya está cancelada.'),
        },
    ),
)(ReservaViewSet)
