from django.contrib import messages

from .roles import obtener_rol, ADMINISTRADOR, TERAPEUTA, CLIENTE


class RestriccionPorRolMiddleware:
    """
    Restringe las áreas internas según el rol del usuario autenticado:
      /administrador/  -> solo Administrador
      /terapeuta/      -> Administrador y Terapeuta
    Las peticiones sin sesión las maneja @login_required de cada vista.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user

        if user.is_authenticated:
            rol = obtener_rol(user)
            ruta = request.path

            if ruta.startswith('/administrador/') and rol != ADMINISTRADOR:
                return self._denegar(request, user, rol)

            if ruta.startswith('/terapeuta/') and rol not in (ADMINISTRADOR, TERAPEUTA):
                return self._denegar(request, user, rol)

        return self.get_response(request)

    def _denegar(self, request, user, rol):
        # Import local para evitar importaciones circulares con views.py
        from usuarioApp.views import _redirect_by_role

        # El aviso solo se muestra al cliente, porque su panel sí muestra mensajes
        if rol == CLIENTE:
            messages.error(request, "No tienes permiso para acceder a esa sección.")

        return _redirect_by_role(user)