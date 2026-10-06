#este es para probar el token de autenticación de la API REST
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def yo(request):
    """Endpoint protegido de prueba: dice quién es el usuario del token."""
    return Response({'usuario': request.user.username})