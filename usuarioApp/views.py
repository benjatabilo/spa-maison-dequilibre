import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.contrib import messages

# Importamos los modelos de las otras apps y de la propia usuarioApp
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from .models import Reserva
from .forms import ReservaForm, PerfilUsuarioForm


# --- FUNCIÓN AUXILIAR PARA JSON (Mantenida por si conservas info_spa.json) ---
def _cargar_json(nombre_archivo):
    ruta = os.path.join(settings.BASE_DIR, 'usuarioApp', 'data', nombre_archivo)
    if os.path.exists(ruta):
        with open(ruta, encoding='utf-8') as archivo:
            return json.load(archivo)
    return {}


# --- VISTAS PÚBLICAS Y DE CONSULTA ---

def inicio(request):
    """Página de inicio del Spa."""
    info = _cargar_json('info_spa.json')
    contexto = {
        'info': info,
    }
    return render(request, 'usuario/inicio.html', contexto)


def terapias(request):
    """Catálogo de terapias desde la base de datos (con buscador)."""
    query = request.GET.get('q', '')
    if query:
        lista_terapias = Terapia.objects.filter(nombre__icontains=query)
    else:
        lista_terapias = Terapia.objects.all()

    contexto = {
        'terapias': lista_terapias,
        'hay_terapias': lista_terapias.exists(),
        'total_terapias': lista_terapias.count(),
        'query': query,
    }
    return render(request, 'usuario/terapias.html', contexto)


def terapeutas(request):
    """Catálogo de terapeutas desde la base de datos."""
    lista_terapeutas = Terapeuta.objects.all()
    contexto = {
        'terapeutas': lista_terapeutas,
        'hay_terapeutas': lista_terapeutas.exists(),
    }
    return render(request, 'usuario/terapeutas.html', contexto)


# --- AUTENTICACIÓN (LOGIN, LOGOUT Y REGISTRO) ---

def registro_view(request):
    """Permite a un nuevo cliente registrarse en la plataforma."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            messages.success(request, f"Bienvenido/a {usuario.username}, tu cuenta ha sido creada con éxito.")
            return redirect('inicio_usuario')
    else:
        form = UserCreationForm()
    return render(request, 'usuario/registro.html', {'form': form})


def logout_view(request):
    """Cierra la sesión del cliente."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('inicio_usuario')


# --- CRUD DE RESERVAS DEL CLIENTE ---

@login_required
def crear_reserva(request):
    """Permite al cliente crear/agendar una nueva reserva."""
    terapia_id = request.GET.get('terapia_id')
    initial_data = {}
    if terapia_id:
        initial_data['terapia'] = terapia_id

    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.usuario = request.user  # Vincula la reserva al cliente autenticado
            reserva.save()
            messages.success(request, "¡Tu reserva se ha registrado correctamente!")
            return redirect('mis_reservas')
    else:
        form = ReservaForm(initial=initial_data)

    return render(request, 'usuario/reserva_form.html', {'form': form, 'titulo': 'Agendar Cita'})


@login_required
def mis_reservas(request):
    """Lista todas las reservas realizadas por el cliente autenticado."""
    reservas = Reserva.objects.filter(usuario=request.user)
    return render(request, 'usuario/mis_reservas.html', {'reservas': reservas})


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
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            messages.success(request, "Reserva actualizada con éxito.")
            return redirect('mis_reservas')
    else:
        form = ReservaForm(instance=reserva)

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


# --- PERFIL DE USUARIO / CLIENTE ---

@login_required
def mi_perfil(request):
    """Permite al cliente visualizar y actualizar sus datos personales."""
    if request.method == 'POST':
        form = PerfilUsuarioForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tus datos de perfil se han actualizado correctamente.")
            return redirect('mi_perfil')
    else:
        form = PerfilUsuarioForm(instance=request.user)

    return render(request, 'usuario/perfil.html', {'form': form})