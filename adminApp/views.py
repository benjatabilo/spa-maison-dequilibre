import os
import json
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import RestrictedError
from PIL import Image
from django.contrib.auth.decorators import login_required
from .models import Terapia
from .forms import TerapiaForm, TerapeutaForm, ClienteForm, usuario_de_terapeuta
from terapeutaApp.models import Terapeuta
from django.contrib.auth.models import User, Group

def _cargar_json(nombre_archivo, valor_por_defecto=None):
    """
    Lee un archivo JSON ubicado en adminApp/data/ y retorna su contenido.
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

    query = request.GET.get('q', '').strip()

    lista_clientes = (
        User.objects
        .exclude(is_superuser=True)
        .exclude(groups__name__in=['Administrador', 'Terapeuta'])
        .distinct()
        .order_by('username')
    )
    if query:
        lista_clientes = lista_clientes.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    total_activos = lista_clientes.filter(is_active=True).count()

    contexto = {
        'clientes': lista_clientes,
        'total_clientes': lista_clientes.count(),
        'total_activos': total_activos,
        'query': query,
        'seccion_activa': 'clientes',
    }
    return render(request, 'administrador/clientes.html', contexto)


@login_required
def editar_cliente(request, pk):
    """Modificar: edita los datos basicos de un cliente."""
    cliente = get_object_or_404(User, pk=pk, groups__name='Cliente')

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Los datos del cliente se actualizaron correctamente.')
            return redirect('clientes_admin')
        messages.error(request, 'No se pudo actualizar el cliente. Revisa los errores del formulario.')
    else:
        form = ClienteForm(instance=cliente)

    contexto = {
        'form': form,
        'cliente': cliente,
        'seccion_activa': 'clientes',
    }
    return render(request, 'administrador/cliente_form.html', contexto)


@login_required
def cambiar_estado_cliente(request, pk):
    """
    'Eliminar' de un cliente = desactivar su cuenta, no borrarla.
    Reserva.usuario usa on_delete=CASCADE: borrar el User de verdad
    destruiria todo su historial de reservas. Desactivar bloquea su
    acceso (no puede iniciar sesion) sin perder ese historial.
    """
    cliente = get_object_or_404(User, pk=pk, groups__name='Cliente')

    if request.method == 'POST':
        cliente.is_active = not cliente.is_active
        cliente.save()
        if cliente.is_active:
            messages.success(request, f'La cuenta de {cliente.username} fue reactivada.')
        else:
            messages.success(request, f'La cuenta de {cliente.username} fue desactivada.')
        return redirect('clientes_admin')

    return redirect('clientes_admin')


@login_required
def mi_perfil(request):
    perfil = _cargar_json('perfil.json', {})

    contexto = {
        'perfil': perfil,
        'seccion_activa': 'perfil',
        'sin_datos': not perfil,
    }
    return render(request, 'administrador/perfil.html', contexto)


# --- CRUD DE TERAPIAS (mantenedor con base de datos - Django ORM) ---

@login_required
def lista_terapias(request):
    """
    Mostrar Todos + Buscar: lista las terapias guardadas en la base de
    datos, con un buscador opcional por nombre o descripcion.
    """
    query = request.GET.get('q', '').strip()

    terapias = Terapia.objects.all().order_by('nombre')
    if query:
        terapias = terapias.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    contexto = {
        'terapias': terapias,
        'total_terapias': terapias.count(),
        'query': query,
        'seccion_activa': 'terapias',
    }
    return render(request, 'administrador/terapias_lista.html', contexto)


@login_required
def crear_terapia(request):
    """Agregar: crea una nueva terapia (mantenedor) en la base de datos."""
    if request.method == 'POST':
        form = TerapiaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'La terapia se registró correctamente.')
            return redirect('lista_terapias')
        messages.error(request, 'No se pudo guardar la terapia. Revisa los errores del formulario.')
    else:
        form = TerapiaForm()

    contexto = {
        'form': form,
        'titulo': 'Agregar Terapia',
        'seccion_activa': 'terapias',
    }
    return render(request, 'administrador/terapia_form.html', contexto)


@login_required
def editar_terapia(request, pk):
    """Modificar: edita una terapia existente, precargando sus datos."""
    terapia = get_object_or_404(Terapia, pk=pk)

    if request.method == 'POST':
        form = TerapiaForm(request.POST, request.FILES, instance=terapia)
        if form.is_valid():
            form.save()
            messages.success(request, 'La terapia se actualizó correctamente.')
            return redirect('lista_terapias')
        messages.error(request, 'No se pudo actualizar la terapia. Revisa los errores del formulario.')
    else:
        form = TerapiaForm(instance=terapia)

    contexto = {
        'form': form,
        'titulo': 'Modificar Terapia',
        'terapia': terapia,
        'seccion_activa': 'terapias',
    }
    return render(request, 'administrador/terapia_form.html', contexto)


@login_required
def eliminar_terapia(request, pk):
    """
    Eliminar: borra una terapia, pidiendo confirmacion previa.

    Reserva.terapia usa on_delete=RESTRICT, asi que Django no permite
    borrar una terapia si existen reservas que la referencian. Se captura
    ese caso para mostrar un mensaje claro en vez de un Error 500.
    """
    terapia = get_object_or_404(Terapia, pk=pk)

    if request.method == 'POST':
        try:
            terapia.delete()
            messages.success(request, 'La terapia fue eliminada correctamente.')
        except RestrictedError:
            messages.error(
                request,
                f'No se puede eliminar "{terapia.nombre}" porque tiene reservas '
                'asociadas. Cancela o reasigna esas reservas antes de eliminarla.'
            )
        return redirect('lista_terapias')

    contexto = {
        'terapia': terapia,
        'total_reservas': terapia.reservas.count(),
        'seccion_activa': 'terapias',
    }
    return render(request, 'administrador/terapia_confirm_delete.html', contexto)


# --- CRUD DE TERAPEUTAS (mantenedor de terapeutaApp, gestionado desde aqui) ---

@login_required
def lista_terapeutas(request):
    """Mostrar Todos + Buscar: lista los terapeutas registrados."""
    query = request.GET.get('q', '').strip()

    terapeutas = Terapeuta.objects.all().order_by('nombre')
    if query:
        terapeutas = terapeutas.filter(
            Q(nombre__icontains=query) |
            Q(profesion__icontains=query) |
            Q(correo__icontains=query)
        )

    contexto = {
        'terapeutas': terapeutas,
        'total_terapeutas': terapeutas.count(),
        'query': query,
        'seccion_activa': 'terapeutas',
    }
    return render(request, 'administrador/terapeutas_lista.html', contexto)


@login_required
def crear_terapeuta(request):
    """Agregar: registra un nuevo terapeuta."""
    if request.method == 'POST':
        form = TerapeutaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'El terapeuta se registró correctamente y ya puede iniciar sesión con su correo y contraseña.')
            return redirect('lista_terapeutas')
        messages.error(request, 'No se pudo guardar el terapeuta. Revisa los errores del formulario.')
    else:
        form = TerapeutaForm()

    contexto = {
        'form': form,
        'titulo': 'Agregar Terapeuta',
        'seccion_activa': 'terapeutas',
    }
    return render(request, 'administrador/terapeuta_form.html', contexto)


@login_required
def editar_terapeuta(request, pk):
    """Modificar: edita un terapeuta existente."""
    terapeuta = get_object_or_404(Terapeuta, pk=pk)

    if request.method == 'POST':
        form = TerapeutaForm(request.POST, request.FILES, instance=terapeuta)
        if form.is_valid():
            form.save()
            messages.success(request, 'El terapeuta se actualizó correctamente.')
            return redirect('lista_terapeutas')
        messages.error(request, 'No se pudo actualizar el terapeuta. Revisa los errores del formulario.')
    else:
        form = TerapeutaForm(instance=terapeuta)

    contexto = {
        'form': form,
        'titulo': 'Modificar Terapeuta',
        'terapeuta': terapeuta,
        'seccion_activa': 'terapeutas',
    }
    return render(request, 'administrador/terapeuta_form.html', contexto)


@login_required
def eliminar_terapeuta(request, pk):
    """
    Eliminar: borra un terapeuta, pidiendo confirmacion previa.
    Reserva.terapeuta tambien usa on_delete=RESTRICT, mismo caso que Terapia.
    """
    terapeuta = get_object_or_404(Terapeuta, pk=pk)

    if request.method == 'POST':
        try:
            usuario = usuario_de_terapeuta(terapeuta.correo)
            with transaction.atomic():
                terapeuta.delete()
                if usuario:
                    usuario.delete()  # también se elimina su cuenta de acceso
            messages.success(request, 'El terapeuta fue eliminado correctamente.')
        except RestrictedError:
            messages.error(
                request,
                f'No se puede eliminar a "{terapeuta.nombre}" porque tiene reservas '
                'asociadas. Cancela o reasigna esas reservas antes de eliminarlo.'
            )
        return redirect('lista_terapeutas')

    contexto = {
        'terapeuta': terapeuta,
        'total_reservas': terapeuta.reservas.count(),
        'seccion_activa': 'terapeutas',
    }
    return render(request, 'administrador/terapeuta_confirm_delete.html', contexto)