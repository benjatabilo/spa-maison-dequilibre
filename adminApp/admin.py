from django.contrib import admin
from .models import Terapia


@admin.register(Terapia)
class TerapiaAdmin(admin.ModelAdmin):
    # Columnas visibles en el listado de Django Admin
    list_display = ('id', 'nombre', 'precio', 'duracion', 'creado')
    list_display_links = ('id', 'nombre')

    # Buscador de Django Admin (barra superior)
    search_fields = ('nombre', 'descripcion')

    # Filtros laterales
    list_filter = ('duracion',)
    ordering = ('nombre',)
    readonly_fields = ('creado',)
    list_per_page = 20

    fieldsets = (
        ('Datos de la terapia', {'fields': ('nombre', 'precio', 'duracion', 'descripcion')}),
        ('Imagen', {'fields': ('imagen',)}),
        ('Metadatos', {'fields': ('creado',)}),
    )