import logging

from django.db.models.deletion import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def manejador_excepciones(exc, context):
    """
    Manejo seguro de errores: TODA respuesta de error de la API sale en JSON y nunca
    muestra trazas, rutas del servidor ni detalles internos.
      - Errores de DRF (400, 401, 403, 404, 405, 429...) -> los formatea DRF.
      - Intentar borrar algo con reservas asociadas (on_delete=RESTRICT) -> 409 Conflict.
      - Cualquier otro error inesperado -> 500 con mensaje genérico (el detalle va al log).
    """
    if isinstance(exc, (RestrictedError, ProtectedError)):
        return Response(
            {'detail': 'No se puede eliminar: el registro tiene reservas asociadas.',
             'code': 'registro_en_uso'},
            status=status.HTTP_409_CONFLICT,
        )

    respuesta = exception_handler(exc, context)
    if respuesta is not None:
        return respuesta

    logger.exception('Error no controlado en la API', exc_info=exc)
    return Response(
        {'detail': 'Ocurrió un error interno en el servidor.', 'code': 'error_interno'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )