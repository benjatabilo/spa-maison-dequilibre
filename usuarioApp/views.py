import os
import json
from django.shortcuts import render
from django.conf import settings


# Función reutilizable para leer cualquier archivo JSON de esta app.
def _cargar_json(nombre_archivo):
    ruta = os.path.join(settings.BASE_DIR, 'usuarioApp', 'data', nombre_archivo)
    with open(ruta, encoding='utf-8') as archivo:
        datos = json.load(archivo)
    return datos


def inicio(request):
    info = _cargar_json('info_spa.json')
    contexto = {
        'info': info,
    }
    return render(request, 'usuario/inicio.html', contexto)


def terapias(request):
    lista_terapias = _cargar_json('terapias.json')
    hay_terapias = len(lista_terapias) > 0

    contexto = {
        'terapias': lista_terapias,
        'hay_terapias': hay_terapias,
        'total_terapias': len(lista_terapias),
    }
    return render(request, 'usuario/terapias.html', contexto)


def terapeutas(request):
    lista_terapeutas = _cargar_json('terapeutas.json')
    hay_terapeutas = len(lista_terapeutas) > 0

    contexto = {
        'terapeutas': lista_terapeutas,
        'hay_terapeutas': hay_terapeutas,
    }
    return render(request, 'usuario/terapeutas.html', contexto)


def login_view(request):
    # Vista temporal: mas adelante aqui va el formulario real de inicio de sesion.
    return render(request, 'usuario/login.html')
