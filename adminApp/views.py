import os
import json
from django.conf import settings
from django.shortcuts import render
from PIL import Image
from django.contrib.auth.decorators import login_required

def _cargar_json(nombre_archivo, valor_por_defecto=None):
    """
    Lee un archivo JSON ubicado en adminApp/data/ y retorna su contenido.

    Si el archivo no existe o tiene un formato invalido, no se detiene
    la ejecucion del servidor: se retorna 'valor_por_defecto' (una lista
    o diccionario vacio segun corresponda) para que la vista y la
    plantilla puedan seguir funcionando con datos vacios en vez de
    mostrar un Error 500.
    """
    if valor_por_defecto is None:
        valor_por_defecto = []

    ruta = os.path.join(settings.BASE_DIR, 'adminApp', 'data', nombre_archivo)

    try:
        with open(ruta, encoding='utf-8') as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return valor_por_defecto
    except json.JSONDecodeError:
        return valor_por_defecto


def _info_imagen(nombre_archivo):
    """
    Usa Pillow (libreria externa) para leer las dimensiones reales y el
    peso en disco de una imagen dentro de static/images/.
    """
    ruta = os.path.join(settings.BASE_DIR, 'static', 'images', nombre_archivo)

    try:
        with Image.open(ruta) as imagen:
            ancho, alto = imagen.size
            formato = imagen.format
    except (FileNotFoundError, OSError):
        return None

    peso_kb = round(os.path.getsize(ruta) / 1024, 1)

    return {
        'ancho': ancho,
        'alto': alto,
        'formato': formato,
        'peso_kb': peso_kb,
    }


DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _construir_grafico_citas(citas):
    conteo = {dia: 0 for dia in DIAS_SEMANA}
    for cita in citas:
        dia = cita.get('dia')
        if dia in conteo:
            conteo[dia] += 1

    maximo = max(conteo.values()) if conteo.values() else 0
    maximo = maximo if maximo > 0 else 1

    grafico = []
    for dia in DIAS_SEMANA:
        cantidad = conteo[dia]
        grafico.append({
            'dia': dia,
            'cantidad': cantidad,
            'porcentaje': round((cantidad / maximo) * 100),
        })
    return grafico

@login_required
def panel(request):
    resumen = _cargar_json('resumen.json', {})
    citas = _cargar_json('citas.json', [])

    citas_ordenadas = sorted(
        citas,
        key=lambda cita: DIAS_SEMANA.index(cita.get('dia')) if cita.get('dia') in DIAS_SEMANA else 99
    )
    grafico_citas = _construir_grafico_citas(citas)
    info_imagen = _info_imagen('espacio_recepcion.jpg')

    contexto = {
        'resumen': resumen,
        'citas': citas_ordenadas,
        'total_citas': len(citas),
        'grafico_citas': grafico_citas,
        'info_imagen': info_imagen,
        'seccion_activa': 'panel',
        'sin_datos': not resumen and not citas,
    }
    return render(request, 'administrador/panel.html', contexto)

@login_required
def turnos(request):
    lista_turnos = _cargar_json('turnos.json', [])

    turnos_activos = [t for t in lista_turnos if t.get('estado') == 'Activo']
    turnos_libres = [t for t in lista_turnos if t.get('estado') != 'Activo']
    info_imagen = _info_imagen('espacio_masaje.jpg')

    contexto = {
        'turnos': lista_turnos,
        'total_turnos': len(lista_turnos),
        'total_activos': len(turnos_activos),
        'total_libres': len(turnos_libres),
        'info_imagen': info_imagen,
        'seccion_activa': 'turnos',
        'sin_datos': not lista_turnos,
    }
    return render(request, 'administrador/turnos.html', contexto)

@login_required
def clientes(request):
    lista_clientes = _cargar_json('clientes.json', [])

    clientes_frecuentes = [c for c in lista_clientes if c.get('estado') == 'Frecuente']

    contexto = {
        'clientes': lista_clientes,
        'total_clientes': len(lista_clientes),
        'total_frecuentes': len(clientes_frecuentes),
        'seccion_activa': 'clientes',
        'sin_datos': not lista_clientes,
    }
    return render(request, 'administrador/clientes.html', contexto)

@login_required
def mi_perfil(request):
    perfil = _cargar_json('perfil.json', {})

    contexto = {
        'perfil': perfil,
        'seccion_activa': 'perfil',
        'sin_datos': not perfil,
    }
    return render(request, 'administrador/perfil.html', contexto)