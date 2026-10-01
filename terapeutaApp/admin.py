from django.contrib import admin
from .models import Terapeuta


@admin.register(Terapeuta)
class TerapeutaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'profesion', 'correo')
    list_display_links = ('id', 'nombre')
    search_fields = ('nombre', 'profesion', 'correo')
    ordering = ('nombre',)
    list_per_page = 20
    filter_horizontal = ('terapias',)

    fieldsets = (
        ('Datos del terapeuta', {'fields': ('nombre', 'profesion', 'correo', 'terapias')}),
        ('Archivos', {'fields': ('foto', 'certificado')}),
    )