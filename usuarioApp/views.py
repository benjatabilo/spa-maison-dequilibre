import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_time
from django.utils import timezone
from django.http import JsonResponse
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from .models import Reserva
from .forms import ReservaForm, PerfilUsuarioForm, RegistroForm, HORAS_DISPONIBLES
from .roles import obtener_rol, ADMINISTRADOR, TERAPEUTA

# --- FUNCIÓN AUXILIAR PARA REDIRECCIÓN SEGÚN ROL DE USUARIO ---
def _redirect_by_role(user):
    """Redirige al usuario a su panel según su rol."""
    rol = obtener_rol(user)
    if rol == ADMINISTRADOR:
        return redirect('panel_admin')
    if rol == TERAPEUTA:
        return redirect('rendimiento_terapeuta')
    return redirect('mi_perfil')

# --- FUNCIÓN AUXILIAR PARA JSON ---
def _cargar_json(nombre_archivo):
    ruta = os.path.join(settings.BASE_DIR, 'usuarioApp', 'data', nombre_archivo)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as archivo:
            return json.load(archivo)
    return {}


# --- VISTAS PÚBLICAS Y DE CONSULTA ---
def _cargar_json(nombre_archivo):
    """Carga un archivo JSON desde la carpeta static/data/ del proyecto."""
    ruta_archivo = os.path.join(settings.BASE_DIR, 'static', 'data', nombre_archivo)
    with open(ruta_archivo, 'r', encoding='utf-8') as file:
        return json.load(file)

def inicio(request):
    """Página de inicio del Spa."""
    info = _cargar_json('info_spa.json')
    contexto = {
        'info': info,
    }
    return render(request, 'usuario/inicio.html', contexto)

def terapias(request):
    """Catálogo de terapias desde la base de datos (con buscador)."""
    query = request.GET.get('q', '').strip()

    lista_terapias = Terapia.objects.all().order_by('nombre')
    if query:
        lista_terapias = lista_terapias.filter(
            Q(nombre__icontains=query) | Q(descripcion__icontains=query)
        )

    contexto = {
        'terapias': lista_terapias,
        'total_terapias': lista_terapias.count(),
        'query': query,
    }
    return render(request, 'usuario/terapias.html', contexto)

def terapeutas(request):
    """Directorio de terapeutas desde la base de datos."""
    lista_terapeutas = Terapeuta.objects.all().order_by('nombre')
    return render(request, 'usuario/terapeutas.html', {'terapeutas': lista_terapeutas})

# --- AUTENTICACIÓN (LOGIN, LOGOUT Y REGISTRO) ---

def login_view(request):
    """Inicia sesión con usuario o correo y redirige según el rol."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password_input = request.POST.get('password', '')

        usuario = authenticate(request, username=login_input, password=password_input)

        if usuario is None and '@' in login_input:
            user_obj = User.objects.filter(email__iexact=login_input).first()
            if user_obj:
                usuario = authenticate(request, username=user_obj.username, password=password_input)

        if usuario is not None:
            login(request, usuario)
            messages.success(request, f"¡Bienvenido/a de nuevo, {usuario.username}!")

            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return _redirect_by_role(usuario)

        messages.error(request, "Usuario/correo o contraseña incorrectos.")

    return render(request, 'usuario/login.html')

def registro_view(request):
    """Permite a un nuevo cliente registrarse en la plataforma."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()

            # Todo registro público queda como Cliente
            grupo_cliente, _ = Group.objects.get_or_create(name='Cliente')
            usuario.groups.add(grupo_cliente)

            login(request, usuario)
            messages.success(request, f"Bienvenido/a {usuario.first_name}, tu cuenta ha sido creada con éxito.")
            return _redirect_by_role(usuario)
        messages.error(request, "Revisa los datos ingresados, hay errores en el formulario.")
    else:
        form = RegistroForm()

    return render(request, 'usuario/registro.html', {'form': form})

def logout_view(request):
    """Cierra la sesión activa del usuario y vuelve a la página de inicio de sesión."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')

@login_required
def mi_panel(request):
    """Lleva al usuario a su panel según su rol (admin, terapeuta o cliente)."""
    return _redirect_by_role(request.user)

# --- CRUD DE RESERVAS DEL CLIENTE ---

@login_required
def ajax_terapeutas_de_terapia(request, terapia_id):
    """
    Devuelve en JSON los terapeutas que realizan una terapia especifica.
    Usado por el formulario de reserva para filtrar el select de terapeuta
    apenas el cliente elige una terapia.
    """
    terapia = get_object_or_404(Terapia, pk=terapia_id)
    terapeutas = terapia.terapeutas.all().order_by('nombre').values('id', 'nombre')
    return JsonResponse({'terapeutas': list(terapeutas)})


@login_required
def ajax_terapias_de_terapeuta(request, terapeuta_id):
    """
    Devuelve en JSON las terapias que realiza un terapeuta especifico.
    Usado por el formulario de reserva para filtrar el select de terapia
    apenas el cliente elige un terapeuta directamente.
    """
    terapeuta = get_object_or_404(Terapeuta, pk=terapeuta_id)
    terapias = terapeuta.terapias.all().order_by('nombre').values('id', 'nombre', 'precio', 'duracion')
    return JsonResponse({'terapias': list(terapias)})


@login_required
def ajax_horas_ocupadas(request):
    """
    Devuelve en JSON las horas (de las 8 franjas de 9:00 a 16:00) que YA
    estan tomadas para un terapeuta en una fecha dada, para que el
    formulario de reserva las deshabilite en el select de hora.
    """
    terapeuta_id = request.GET.get('terapeuta_id')
    fecha = parse_date(request.GET.get('fecha', ''))
    excluir_reserva_id = request.GET.get('excluir_reserva_id')

    if not (terapeuta_id and fecha):
        return JsonResponse({'horas_ocupadas': []})

    ocupadas_qs = Reserva.objects.filter(
        terapeuta_id=terapeuta_id, fecha=fecha
    ).exclude(estado='CANCELADA')

    if excluir_reserva_id:
        ocupadas_qs = ocupadas_qs.exclude(pk=excluir_reserva_id)

    horas_ocupadas = [r.hora.strftime('%H:%M') for r in ocupadas_qs]

    return JsonResponse({'horas_ocupadas': horas_ocupadas})


@login_required
def crear_reserva(request):
    """Permite al cliente crear/agendar una nueva reserva."""
    initial_data = {}
    if request.GET.get('terapia_id'):
        initial_data['terapia'] = request.GET.get('terapia_id')
    if request.GET.get('terapeuta_id'):
        initial_data['terapeuta'] = request.GET.get('terapeuta_id')

    if request.method == 'POST':
        form = ReservaForm(request.POST, user=request.user)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.usuario = request.user
            reserva.save()
            messages.success(request, "¡Tu reserva se ha registrado correctamente!")
            return redirect('mis_reservas')
        messages.error(request, "No se pudo registrar la reserva. Revisa los errores del formulario.")
    else:
        form = ReservaForm(initial=initial_data, user=request.user)

    return render(request, 'usuario/reserva_form.html', {'form': form, 'titulo': 'Agendar Cita'})

@login_required
def mis_reservas(request):
    """Lista las reservas del cliente con búsqueda y filtros."""
    todas = Reserva.objects.filter(usuario=request.user)
    reservas = todas.select_related('terapia', 'terapeuta')

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    desde = request.GET.get('desde', '').strip()
    hasta = request.GET.get('hasta', '').strip()

    # Buscar por nombre de terapia o de terapeuta
    if q:
        reservas = reservas.filter(
            Q(terapia__nombre__icontains=q) | Q(terapeuta__nombre__icontains=q)
        )

    # Filtrar por estado (solo si es un estado válido)
    estados_validos = [codigo for codigo, _ in Reserva.ESTADOS]
    if estado in estados_validos:
        reservas = reservas.filter(estado=estado)
    else:
        estado = ''

    # Filtrar por rango de fechas (parse_date devuelve None si el formato es inválido)
    fecha_desde = parse_date(desde) if desde else None
    fecha_hasta = parse_date(hasta) if hasta else None
    if fecha_desde:
        reservas = reservas.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        reservas = reservas.filter(fecha__lte=fecha_hasta)

    contexto = {
        'reservas': reservas,
        'total_general': todas.count(),
        'total_filtrado': reservas.count(),
        'estados': Reserva.ESTADOS,
        'q': q,
        'estado': estado,
        'desde': desde if fecha_desde else '',
        'hasta': hasta if fecha_hasta else '',
        'hay_filtros': bool(q or estado or fecha_desde or fecha_hasta),
    }
    return render(request, 'usuario/mis_reservas.html', contexto)

@login_required
def detalle_reserva(request, pk):
    """Muestra el detalle individual de una reserva del cliente."""
    reserva = get_object_or_404(Reserva, pk=pk, usuario=request.user)
    return render(request, 'usuario/reserva_detail.html', {'reserva': reserva})


@login_required
def editar_reserva(request, pk):
    """Permite al cliente editar los datos de su reserva."""
    reserva = get_object_or_404(Reserva, pk=pk, usuario=request.user)

    if reserva.estado in ['COMPLETADA', 'CANCELADA']:
        messages.error(request, "No puedes modificar una reserva cancelada o completada.")
        return redirect('mis_reservas')

    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Reserva actualizada con éxito.")
            return redirect('mis_reservas')
        messages.error(request, "No se pudo actualizar la reserva. Revisa los errores del formulario.")
    else:
        form = ReservaForm(instance=reserva, user=request.user)

    return render(request, 'usuario/reserva_form.html', {'form': form, 'titulo': 'Modificar Reserva'})

@login_required
def cancelar_reserva(request, pk):
    """Permite al cliente cancelar o eliminar su reserva."""
    reserva = get_object_or_404(Reserva, pk=pk, usuario=request.user)

    if request.method == 'POST':
        reserva.estado = 'CANCELADA'
        reserva.save()
        messages.success(request, "La reserva ha sido cancelada.")
        return redirect('mis_reservas')

    return render(request, 'usuario/reserva_confirm_delete.html', {'reserva': reserva})

@login_required
def eliminar_reserva(request, pk):
    """Elimina definitivamente una reserva del cliente (solo si ya está cancelada)."""
    reserva = get_object_or_404(Reserva, pk=pk, usuario=request.user)

    if reserva.estado != 'CANCELADA':
        messages.error(
            request,
            "Solo puedes eliminar reservas que ya están canceladas. Cancela la cita primero."
        )
        return redirect('mis_reservas')

    if request.method == 'POST':
        reserva.delete()
        messages.success(request, "La reserva fue eliminada definitivamente.")
        return redirect('mis_reservas')

    return render(request, 'usuario/reserva_eliminar.html', {'reserva': reserva})

# --- PERFIL DE USUARIO / CLIENTE ---

@login_required
def mi_perfil(request):
    """Resumen del cliente: métricas, próximas citas y edición de datos personales."""
    activas = Reserva.objects.filter(
        usuario=request.user, estado__in=['PENDIENTE', 'CONFIRMADA']
    )
    proximas = (
        activas.filter(fecha__gte=timezone.localdate())
        .select_related('terapia', 'terapeuta')
        .order_by('fecha', 'hora')[:4]
    )

    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tus datos de perfil se han actualizado correctamente.")
            return redirect('mi_perfil')
        messages.error(request, "No se pudieron guardar los cambios. Revisa los datos ingresados.")
    else:
        form = PerfilUsuarioForm(instance=request.user)

    contexto = {
        'form': form,
        'proximas': proximas,
        'total_activas': activas.count(),
    }
    return render(request, 'usuario/perfil.html', contexto)