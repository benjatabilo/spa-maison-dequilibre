from django.contrib import admin
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    # Columnas de la lista: muestran las relaciones (cliente, terapia, terapeuta)
    list_display = ('id', 'usuario', 'terapia', 'terapeuta', 'fecha', 'hora', 'estado')
    list_display_links = ('id', 'usuario')
    list_editable = ('estado',)          # cambiar el estado directo desde la lista
    list_select_related = ('usuario', 'terapia', 'terapeuta')  # evita consultas repetidas

    # Buscar por cliente, terapia o terapeuta
    search_fields = (
        'usuario__username',
        'usuario__first_name',
        'usuario__last_name',
        'usuario__email',
        'terapia__nombre',
        'terapeuta__nombre',
    )

    # Filtros laterales
    list_filter = ('estado', 'fecha', 'terapia', 'terapeuta')
    date_hierarchy = 'fecha'
    ordering = ('-fecha', '-hora')
    readonly_fields = ('creado',)
    list_per_page = 20

    fieldsets = (
        ('Cliente y servicio', {'fields': ('usuario', 'terapia', 'terapeuta')}),
        ('Agenda', {'fields': ('fecha', 'hora', 'estado')}),
        ('Detalles', {'fields': ('observaciones', 'creado')}),
    )

    # Acciones masivas para el personal
    actions = ('marcar_confirmada', 'marcar_completada', 'marcar_cancelada')

    @admin.action(description='Marcar reservas seleccionadas como Confirmadas')
    def marcar_confirmada(self, request, queryset):
        actualizadas = queryset.update(estado='CONFIRMADA')
        self.message_user(request, f'{actualizadas} reserva(s) confirmada(s).')

    @admin.action(description='Marcar reservas seleccionadas como Completadas')
    def marcar_completada(self, request, queryset):
        actualizadas = queryset.update(estado='COMPLETADA')
        self.message_user(request, f'{actualizadas} reserva(s) completada(s).')

    @admin.action(description='Marcar reservas seleccionadas como Canceladas')
    def marcar_cancelada(self, request, queryset):
        actualizadas = queryset.update(estado='CANCELADA')
        self.message_user(request, f'{actualizadas} reserva(s) cancelada(s).')