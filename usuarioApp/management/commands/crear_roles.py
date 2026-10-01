from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

CRUD = ['add', 'change', 'delete', 'view']

# (app, modelo, acciones permitidas)
PERMISOS_POR_ROL = {
    'Administrador': [
        ('adminApp', 'terapia', CRUD),
        ('terapeutaApp', 'terapeuta', CRUD),
        ('usuarioApp', 'reserva', CRUD),
        ('auth', 'user', CRUD),          
    ],
    'Terapeuta': [
        ('adminApp', 'terapia', ['view']),
        ('terapeutaApp', 'terapeuta', ['view']),
        ('usuarioApp', 'reserva', ['view']),
    ],
    'Cliente': [
        ('usuarioApp', 'reserva', CRUD),  
    ],
}


class Command(BaseCommand):
    help = 'Crea los grupos Administrador, Terapeuta y Cliente con sus permisos.'

    def handle(self, *args, **options):
        for nombre_rol, definiciones in PERMISOS_POR_ROL.items():
            grupo, creado = Group.objects.get_or_create(name=nombre_rol)
            permisos = []

            for app, modelo, acciones in definiciones:
                for accion in acciones:
                    codename = f'{accion}_{modelo}'
                    try:
                        permisos.append(Permission.objects.get(
                            content_type__app_label=app, codename=codename
                        ))
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f'  Falta el permiso {app}.{codename} (¿migraciones aplicadas?)'
                        ))

            grupo.permissions.set(permisos)
            estado = 'creado' if creado else 'actualizado'
            self.stdout.write(self.style.SUCCESS(
                f'Grupo {nombre_rol} {estado} con {len(permisos)} permisos.'
            ))