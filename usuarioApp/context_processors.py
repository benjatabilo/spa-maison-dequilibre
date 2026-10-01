from .roles import obtener_rol


def rol_usuario(request):
    """Pone 'rol_usuario' disponible en todos los templates."""
    return {'rol_usuario': obtener_rol(request.user)}