#esta pagina me ayuda a crear mis propias excepciones
#las excepciones son para controlar los errores que se producen en la API y devolver un mensaje adecuado al cliente
import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class ConflictoDeEstado(APIException):
    """409 Conflict: la petición es válida, pero choca con el estado actual del recurso."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La operación no es posible en el estado actual del recurso.'
    default_code = 'conflicto_de_estado'


def manejador_excepciones(exc, contexto):
    """
    Un único lugar por donde pasan TODOS los errores de la API. Garantiza que:
      - la respuesta siempre es JSON, con el código HTTP correcto;
      - el mensaje es descriptivo para quien consume la API;
      - nunca se filtran detalles internos (nombres de modelos, rutas, trazas de Python).
    """
    # Django escribe en inglés y con el nombre interno del modelo ("No Terapia matches ...")
    if isinstance(exc, Http404):
        exc = NotFound('El recurso solicitado no existe.')

    # Un error de validación de Django que llega hasta aquí es un error del cliente (400)
    if isinstance(exc, DjangoValidationError):
        return Response({'detail': 'Datos inválidos.', 'errors': exc.messages},
                        status=status.HTTP_400_BAD_REQUEST)

    # Se intentó borrar algo que otras tablas todavía usan (on_delete=RESTRICT/PROTECT)
    if isinstance(exc, (RestrictedError, ProtectedError)):
        return Response({'detail': 'No se puede eliminar: el registro está siendo usado por otros datos.'},
                        status=status.HTTP_409_CONFLICT)

    respuesta = exception_handler(exc, contexto)     # errores "esperados" de DRF (400, 401, 403, 404, 405...)
    if respuesta is not None:
        return respuesta

    # Error inesperado (un bug): el detalle completo va al LOG del servidor, nunca a quien llama
    logger.error('Error no controlado en la API', exc_info=exc)
    return Response({'detail': 'Error interno del servidor. Inténtalo nuevamente más tarde.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)