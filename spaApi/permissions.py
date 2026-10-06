#ESTE ARCHIVO SIRVE PARA DEFINIR PERMISOS DE ACCESO A LOS ENDPOINTS DE LA API REST
from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarioApp.roles import ADMINISTRADOR, obtener_rol


class SoloAdminEscribe(BasePermission):
    """
    Catálogos (terapias, terapeutas): cualquier usuario con token puede CONSULTAR (GET),
    pero solo el Administrador puede crear, modificar o borrar.
    """
    message = 'Solo el Administrador puede crear, modificar o eliminar este recurso.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False                      # sin token -> 401
        if request.method in SAFE_METHODS:    # GET, HEAD, OPTIONS
            return True
        return obtener_rol(request.user) == ADMINISTRADOR   # si no es admin -> 403