"""
Validación de los archivos que llegan por la API.

Un archivo subido se guarda en /media/ y se sirve desde el mismo dominio que la aplicación.
Si se aceptara cualquier cosa (por ejemplo un .html con un <script>), quedaría abierta la puerta
a ataques de XSS. Por eso se revisa:
  1. la extensión permitida,
  2. el CONTENIDO real (cabecera %PDF- o una imagen que Pillow pueda abrir): la extensión sola se
     puede falsificar renombrando el archivo,
  3. el tamaño máximo.
"""
from PIL import Image
from rest_framework import serializers

TAMANO_MAXIMO_MB = 5
TAMANO_MAXIMO_BYTES = TAMANO_MAXIMO_MB * 1024 * 1024

EXTENSIONES_IMAGEN = ('.jpg', '.jpeg', '.png', '.webp')
EXTENSIONES_CERTIFICADO = ('.pdf',) + EXTENSIONES_IMAGEN


def _validar_tamano(archivo, etiqueta):
    if archivo.size > TAMANO_MAXIMO_BYTES:
        raise serializers.ValidationError(f'{etiqueta}: el archivo pesa más de {TAMANO_MAXIMO_MB} MB.')


def _es_imagen_real(archivo):
    try:
        archivo.seek(0)
        Image.open(archivo).verify()
        return True
    except Exception:
        return False
    finally:
        archivo.seek(0)


def validar_imagen(archivo, etiqueta='Imagen'):
    """Imagen JPG, PNG o WEBP real, de hasta 5 MB. Acepta None (el campo es opcional)."""
    if archivo is None:
        return archivo
    nombre = (archivo.name or '').lower()
    if not nombre.endswith(EXTENSIONES_IMAGEN):
        raise serializers.ValidationError(
            f'{etiqueta}: formato no permitido. Usa {", ".join(EXTENSIONES_IMAGEN)}.')
    _validar_tamano(archivo, etiqueta)
    if not _es_imagen_real(archivo):
        raise serializers.ValidationError(f'{etiqueta}: el archivo no es una imagen válida.')
    return archivo


def validar_certificado(archivo):
    """Certificado: PDF real o imagen real, de hasta 5 MB. Acepta None (el campo es opcional)."""
    if archivo is None:
        return archivo
    nombre = (archivo.name or '').lower()
    if not nombre.endswith(EXTENSIONES_CERTIFICADO):
        raise serializers.ValidationError(
            f'Certificado: formato no permitido. Usa {", ".join(EXTENSIONES_CERTIFICADO)}.')
    _validar_tamano(archivo, 'Certificado')
    if nombre.endswith('.pdf'):
        archivo.seek(0)
        cabecera = archivo.read(5)
        archivo.seek(0)
        if cabecera != b'%PDF-':
            raise serializers.ValidationError('Certificado: el archivo no es un PDF válido.')
    elif not _es_imagen_real(archivo):
        raise serializers.ValidationError('Certificado: el archivo no es una imagen válida.')
    return archivo