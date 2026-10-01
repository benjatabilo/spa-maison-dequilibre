from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date

from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from usuarioApp.models import Reserva
from usuarioApp.roles import obtener_rol, ADMINISTRADOR

DIAS_SEMANA = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


# ----------------------------------------------------------------------
# Funciones auxiliares
# ----------------------------------------------------------------------
def _terapeuta_del_usuario(user):
    """
    Vincula el usuario que inició sesión con su ficha de Terapeuta comparando
    el correo (User.email == Terapeuta.correo). Así no se modifica ningún modelo.
    """
    if not user.email:
        return None
    return Terapeuta.objects.filter(correo__iexact=user.email).first()


def _reservas_visibles(user):
    """
    Perfil de solo lectura:
      - Terapeuta: solo las reservas asignadas a él/ella.
      - Administrador (que también puede entrar aquí): todas.
      - Terapeuta sin ficha vinculada: ninguna.
    """
    reservas = Reserva.objects.select_related('usuario', 'terapia', 'terapeuta')
    terapeuta = _terapeuta_del_usuario(user)

    if obtener_rol(user) == ADMINISTRADOR:
        return reservas, terapeuta
    if terapeuta:
        return reservas.filter(terapeuta=terapeuta), terapeuta
    return reservas.none(), None


def _contexto(request, seccion, terapeuta, **extra):
    """Datos comunes que necesita la plantilla base (cabecera y menú)."""
    nombre = (terapeuta.nombre if terapeuta
              else request.user.get_full_name() or request.user.username)
    contexto = {
        'terapeuta': terapeuta,
        'nombre_mostrado': nombre,
        'sin_ficha': terapeuta is None and obtener_rol(request.user) != ADMINISTRADOR,
        'seccion_activa': seccion,
    }
    contexto.update(extra)
    return contexto


def _construir_grilla_semana(reservas, lunes):
    """
    Arma la grilla hora x día de la semana actual a partir de las reservas.
    Las filas son las horas que realmente tienen reservas esa semana.
    """
    fechas = [lunes + timedelta(days=i) for i in range(7)]
    de_la_semana = reservas.filter(fecha__range=(fechas[0], fechas[-1])).exclude(estado='CANCELADA')

    por_slot = {}
    for r in de_la_semana:
        por_slot.setdefault((r.fecha, r.hora), []).append(r)

    horas = sorted({hora for (_, hora) in por_slot})
    grilla = []
    for hora in horas:
        slots = [{'fecha': f, 'citas': por_slot.get((f, hora), [])} for f in fechas]
        grilla.append({'hora': hora, 'slots': slots})

    encabezados = [{'dia': DIAS_SEMANA[f.weekday()], 'fecha': f} for f in fechas]
    return encabezados, grilla


# ----------------------------------------------------------------------
# Vistas (todas de solo lectura: consultar y buscar)
# ----------------------------------------------------------------------
@login_required
def rendimiento(request):
    """Mi agenda: indicadores, terapias más realizadas y calendario semanal."""
    reservas, terapeuta = _reservas_visibles(request.user)

    hoy = timezone.localdate()
    lunes = hoy - timedelta(days=hoy.weekday())

    activas = reservas.exclude(estado='CANCELADA')
    top_terapias = (activas.values('terapia__nombre')
                    .annotate(veces=Count('id'))
                    .order_by('-veces')[:5])

    encabezados, grilla = _construir_grilla_semana(reservas, lunes)

    contexto = _contexto(
        request, 'rendimiento', terapeuta,
        citas_mes=activas.filter(fecha__year=hoy.year, fecha__month=hoy.month).count(),
        total_pendientes=reservas.filter(estado='PENDIENTE').count(),
        total_confirmadas=reservas.filter(estado='CONFIRMADA').count(),
        total_completadas=reservas.filter(estado='COMPLETADA').count(),
        citas_hoy=activas.filter(fecha=hoy).count(),
        proximas=activas.filter(fecha__gte=hoy).order_by('fecha', 'hora')[:5],
        top_terapias=top_terapias,
        encabezados=encabezados,
        grilla=grilla,
        semana_inicio=lunes,
        semana_fin=lunes + timedelta(days=6),
    )
    return render(request, 'terapeuta/panel.html', contexto)


@login_required
def lista_reservas(request):
    """Reservas asignadas, con búsqueda por cliente/terapia y filtros de estado y fecha."""
    reservas, terapeuta = _reservas_visibles(request.user)

    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()
    fecha = parse_date(request.GET.get('fecha', '').strip())

    if q:
        reservas = reservas.filter(
            Q(usuario__username__icontains=q)
            | Q(usuario__first_name__icontains=q)
            | Q(usuario__last_name__icontains=q)
            | Q(terapia__nombre__icontains=q)
        )
    if estado in dict(Reserva.ESTADOS):
        reservas = reservas.filter(estado=estado)
    if fecha:
        reservas = reservas.filter(fecha=fecha)

    contexto = _contexto(
        request, 'reservas', terapeuta,
        reservas=reservas,
        total=reservas.count(),
        estados=Reserva.ESTADOS,
        q=q,
        estado_sel=estado,
        fecha_sel=request.GET.get('fecha', '') if fecha else '',
    )
    return render(request, 'terapeuta/reservas.html', contexto)


@login_required
def lista_terapias(request):
    """Catálogo de terapias (solo consulta) con buscador."""
    terapeuta = _terapeuta_del_usuario(request.user)
    q = request.GET.get('q', '').strip()

    terapias = Terapia.objects.annotate(total_reservas=Count('reservas')).order_by('nombre')
    if q:
        terapias = terapias.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=q))

    contexto = _contexto(
        request, 'terapias', terapeuta,
        terapias=terapias, total=terapias.count(), q=q,
    )
    return render(request, 'terapeuta/terapias.html', contexto)


@login_required
def perfil_inventario(request):
    """Mi perfil: datos de la ficha de Terapeuta, foto y certificado."""
    reservas, terapeuta = _reservas_visibles(request.user)

    contexto = _contexto(
        request, 'perfil', terapeuta,
        total_atenciones=reservas.filter(estado='COMPLETADA').count(),
        total_reservas=reservas.count(),
    )
    return render(request, 'terapeuta/perfil.html', contexto)