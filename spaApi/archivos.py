"""
Cómo se sirven los archivos de /media/.

  - Fotos de terapeutas e imágenes de terapias: PÚBLICAS (se muestran en el catálogo).
  - Certificados de los terapeutas: PRIVADOS. Solo los descarga el Administrador o el propio
    terapeuta dueño del archivo.

Antes, cualquiera que conociera la URL podía bajar un certificado sin iniciar sesión: la API le
ocultaba el campo a los clientes, pero el ARCHIVO estaba en una dirección pública.
"""
import mimetypes
import os
import posixpath

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.static import serve
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from terapeutaApp.models import Terapeuta
from usuarioApp.roles import ADMINISTRADOR, TERAPEUTA, obtener_rol

PREFIJO_CERTIFICADOS = 'terapeutas/certificados'

# Tipos que el navegador puede mostrar sin riesgo. Todo lo demás se obliga a DESCARGAR
# (protege también a archivos viejos subidos antes de que se validara el tipo).
EXTENSIONES_INLINE = ('.pdf', '.png', '.jpg', '.jpeg', '.webp')


@extend_schema(exclude=True)    # es la descarga de un archivo, no un endpoint de datos
@api_view(['GET'])
@authentication_classes([JWTAuthentication, SessionAuthentication])   # sirve para la API (Bearer) y para la web (sesión)
@permission_classes([IsAuthenticated])
def certificado_protegido(request, ruta):
    # Se busca por el nombre guardado en la BASE DE DATOS. Nunca se arma una ruta del disco con
    # texto que escribió el usuario: así no existe el "path traversal" (../../archivo).
    nombre_guardado = f'{PREFIJO_CERTIFICADOS}/{ruta}'
    terapeuta = Terapeuta.objects.filter(certificado=nombre_guardado).first()
    if terapeuta is None:
        raise NotFound('El archivo solicitado no existe.')

    rol = obtener_rol(request.user)
    email = (request.user.email or '').lower()
    es_dueno = rol == TERAPEUTA and bool(email) and terapeuta.correo.lower() == email
    if rol != ADMINISTRADOR and not es_dueno:
        raise PermissionDenied('No tienes permiso para ver este certificado.')

    nombre = os.path.basename(nombre_guardado)
    tipo, _ = mimetypes.guess_type(nombre)
    try:
        respuesta = FileResponse(
            terapeuta.certificado.open('rb'),
            as_attachment=not nombre.lower().endswith(EXTENSIONES_INLINE),
            filename=nombre,
            content_type=tipo or 'application/octet-stream',
        )
    except FileNotFoundError:
        raise NotFound('El archivo solicitado no existe.')
    respuesta['Cache-Control'] = 'private, no-store'    # un archivo privado no debe quedar en cachés compartidas
    return respuesta


def media_publica(request, path):
    """
    Sirve /media/ (imágenes públicas) y EXCLUYE los certificados. No basta con poner antes la ruta
    protegida: con una dirección como /media/terapeutas/../terapeutas/certificados/x.pdf, `serve`
    normalizaría el ".." y se saltaría la protección. Por eso se normaliza y se bloquea aquí.
    """
    normalizada = posixpath.normpath(path).lstrip('/').lower()
    if normalizada == PREFIJO_CERTIFICADOS or normalizada.startswith(PREFIJO_CERTIFICADOS + '/'):
        raise Http404('No encontrado.')
    return serve(request, path, document_root=settings.MEDIA_ROOT)