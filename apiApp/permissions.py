from rest_framework.permissions import SAFE_METHODS, BasePermission

from usuarioApp.roles import ADMINISTRADOR, TERAPEUTA, CLIENTE, obtener_rol


class SoloAdminEscribe(BasePermission):
    """
    Catálogos (terapias y terapeutas): cualquier usuario autenticado puede CONSULTAR (GET),
    pero solo el Administrador puede crear, modificar o eliminar (POST, PUT, PATCH, DELETE).
    Si falla, la API responde 403 Forbidden.
    """
    message = 'Solo el Administrador puede crear, modificar o eliminar este recurso.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return obtener_rol(request.user) == ADMINISTRADOR


class PermisoReservas(BasePermission):
    """
    Reservas:
      Administrador -> todo.
      Cliente       -> CRUD, pero solo sobre SUS reservas (el filtrado lo hace get_queryset).
      Terapeuta     -> solo lectura de las reservas que le asignaron.
    """
    message = 'Tu perfil no tiene permiso para realizar esta operación sobre las reservas.'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        rol = obtener_rol(request.user)
        if rol in (ADMINISTRADOR, CLIENTE):
            return True
        if rol == TERAPEUTA:
            return request.method in SAFE_METHODS
        return False
