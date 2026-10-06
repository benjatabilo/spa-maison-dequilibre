#esta pagina me ayuda a crear mis propias excepciones
from rest_framework import status
from rest_framework.exceptions import APIException


class ConflictoDeEstado(APIException):
    """409 Conflict: la petición es válida, pero choca con el estado actual del recurso."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'La operación no es posible en el estado actual del recurso.'
    default_code = 'conflicto_de_estado'