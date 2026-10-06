#ESTE ARCHIVO SIRVE PARA DEFINIR SERIALIZADORES DE DATOS DE LA API REST
#LOS SERIALIZADORES SON CLASES QUE CONVIERTEN OBJETOS DE PYTHON (MODELOS DE DJANGO) EN JSON Y VICEVERSA, VALIDANDO LOS DATOS RECIBIDOS.
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from adminApp.forms import GRUPO_TERAPEUTA, usuario_de_terapeuta
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta


class TerapiaSerializer(serializers.ModelSerializer):
    """Convierte una Terapia en JSON (y el JSON recibido en una Terapia, validándolo)."""

    class Meta:
        model = Terapia
        fields = ['id', 'nombre', 'precio', 'duracion', 'descripcion', 'imagen', 'creado']
        read_only_fields = ['id', 'creado']      # los pone el servidor, no el cliente

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError('El nombre de la terapia no puede estar vacío.')
        repetidas = Terapia.objects.filter(nombre__iexact=valor)
        if self.instance:                         # al modificar, no se compara contra sí misma
            repetidas = repetidas.exclude(pk=self.instance.pk)
        if repetidas.exists():
            raise serializers.ValidationError('Ya existe una terapia con ese nombre.')
        return valor

    def validate_precio(self, valor):
        if valor <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return valor


# =====================================================================
# Terapeutas: DOS serializers, uno por nivel de información
# =====================================================================
class TerapeutaPublicoSerializer(serializers.ModelSerializer):
    """Lo que ven Cliente y Terapeuta: solo campos públicos (sin correo ni certificado)."""
    terapias = serializers.SlugRelatedField(many=True, read_only=True, slug_field='nombre')

    class Meta:
        model = Terapeuta
        fields = ['id', 'nombre', 'profesion', 'foto', 'terapias']
        read_only_fields = fields


class TerapeutaAdminSerializer(serializers.ModelSerializer):
    """
    Lo que ve y escribe el Administrador: todos los campos.
    `password` es solo de ESCRITURA: sirve para crear la cuenta de acceso del terapeuta,
    pero nunca aparece en ninguna respuesta.
    """
    password = serializers.CharField(
        write_only=True, required=False, style={'input_type': 'password'},
        help_text='Contraseña de la cuenta del terapeuta. Obligatoria al crear.',
    )

    class Meta:
        model = Terapeuta
        fields = ['id', 'nombre', 'profesion', 'correo', 'foto', 'certificado', 'terapias', 'password']
        read_only_fields = ['id']

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError('El nombre no puede estar vacío.')
        return valor.title()                       # formato "Abc", igual que en la web

    def validate_correo(self, valor):
        valor = valor.strip().lower()
        # El correo es también el usuario con que inicia sesión: no puede repetirse
        # ni chocar con la cuenta de otra persona.
        fichas = Terapeuta.objects.filter(correo__iexact=valor)
        cuentas = User.objects.filter(username__iexact=valor) | User.objects.filter(email__iexact=valor)
        if self.instance:
            fichas = fichas.exclude(pk=self.instance.pk)
            propia = usuario_de_terapeuta(self.instance.correo)
            if propia:
                cuentas = cuentas.exclude(pk=propia.pk)
        if fichas.exists() or cuentas.exists():
            raise serializers.ValidationError('Ya existe una cuenta o un terapeuta con ese correo.')
        return valor

    def validate(self, datos):
        password = datos.get('password')
        if self.instance is None and not password:
            raise serializers.ValidationError(
                {'password': 'La contraseña es obligatoria para que el terapeuta pueda iniciar sesión.'})
        if password:
            try:
                validate_password(password)        # largo mínimo, complejidad, etc. (los de settings.py)
            except DjangoValidationError as error:
                raise serializers.ValidationError({'password': list(error.messages)})
        return datos

    def _guardar_cuenta(self, terapeuta, correo_anterior, password):
        """Mantiene la cuenta de acceso (User, grupo Terapeuta) alineada con la ficha, como la web."""
        usuario = usuario_de_terapeuta(correo_anterior) if correo_anterior else None
        if usuario is None and not password:
            return                                 # ficha antigua sin cuenta: no se inventa una
        usuario = usuario or User()
        nombre, _, apellido = terapeuta.nombre.partition(' ')
        usuario.username = terapeuta.correo
        usuario.email = terapeuta.correo
        usuario.first_name = nombre
        usuario.last_name = apellido.strip()
        if password:
            usuario.set_password(password)
        elif not usuario.pk:
            usuario.set_unusable_password()
        usuario.save()
        grupo, _ = Group.objects.get_or_create(name=GRUPO_TERAPEUTA)
        usuario.groups.add(grupo)

    @transaction.atomic
    def create(self, datos):
        password = datos.pop('password', None)
        terapeuta = super().create(datos)
        self._guardar_cuenta(terapeuta, None, password)
        return terapeuta

    @transaction.atomic
    def update(self, instancia, datos):
        password = datos.pop('password', None)
        correo_anterior = instancia.correo
        terapeuta = super().update(instancia, datos)
        self._guardar_cuenta(terapeuta, correo_anterior, password)
        return terapeuta