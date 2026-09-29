import os
import json
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def _cargar_json(nombre_archivo):
    """Lee un archivo JSON ubicado en terapeutaApp/data/ y retorna su contenido."""
    ruta = os.path.join(settings.BASE_DIR, 'terapeutaApp', 'data', nombre_archivo)
    with open(ruta, encoding='utf-8') as archivo:
        datos = json.load(archivo)
    return datos


def _construir_grilla_agenda(agenda):
    """
    Arma una grilla (hora x dia) a partir de la lista de citas.
    Cada celda queda marcada como ocupada (con los datos de la cita)
    o libre, para poder pintar el calendario semanal en la plantilla.
    """
    dias = agenda['dias']
    horarios = agenda['horarios']
    citas = agenda['citas']

    # Diccionario auxiliar para ubicar rapido una cita segun (dia, hora)
    citas_por_slot = {}
    for cita in citas:
        clave = (cita['dia'], cita['hora'])
        citas_por_slot[clave] = cita

    grilla = []
    for hora in horarios:
        fila = {'hora': hora, 'slots': []}
        for dia in dias:
            cita = citas_por_slot.get((dia, hora))
            fila['slots'].append({
                'dia': dia,
                'ocupado': cita is not None,
                'cita': cita,
            })
        grilla.append(fila)

    return dias, grilla

@login_required
def rendimiento(request):
    """
    Vista 1: menu del funcionario + informacion de rendimiento
    + gestion de citas y calendario semanal.
    """
    perfil = _cargar_json('perfil.json')
    agenda = _cargar_json('agenda.json')

    dias, grilla = _construir_grilla_agenda(agenda)

    citas_confirmadas = [c for c in agenda['citas'] if c['estado'] == 'Confirmada']
    citas_pendientes = [c for c in agenda['citas'] if c['estado'] == 'Pendiente']

    contexto = {
        'perfil': perfil,
        'rendimiento': perfil['rendimiento'],
        'dias': dias,
        'grilla': grilla,
        'total_citas_semana': len(agenda['citas']),
        'total_confirmadas': len(citas_confirmadas),
        'total_pendientes': len(citas_pendientes),
        'seccion_activa': 'rendimiento',
    }
    return render(request, 'terapeuta/panel.html', contexto)

@login_required
def perfil_inventario(request):
    """
    Vista 2: informacion de perfil (datos predeterminados del trabajador)
    + modulo de inventario de insumos.
    """
    perfil = _cargar_json('perfil.json')
    inventario = _cargar_json('inventario.json')

    items_con_alerta = [i for i in inventario if i['estado'] != 'Disponible']

    contexto = {
        'perfil': perfil,
        'inventario': inventario,
        'total_items': len(inventario),
        'total_alertas': len(items_con_alerta),
        'seccion_activa': 'perfil',
    }
    return render(request, 'terapeuta/perfil.html', contexto)