#esta pagina me sirve para crear mis propios permisos de acceso a las vistas
from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarioApp.roles import ADMINISTRADOR, CLIENTE, obtener_rol


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


class PermisoReservas(BasePermission):
    """
    Reservas: cualquier usuario con token puede CONSULTAR (cada uno verá solo lo suyo, eso lo
    filtra la vista). Crear, modificar o borrar: solo Cliente y Administrador; el Terapeuta
    únicamente lee las reservas que le asignaron.
    """
    message = 'Tu perfil no puede crear, modificar ni eliminar reservas.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return obtener_rol(request.user) in (ADMINISTRADOR, CLIENTE)