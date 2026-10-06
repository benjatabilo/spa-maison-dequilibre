from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from adminApp.forms import GRUPO_TERAPEUTA, usuario_de_terapeuta
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta
from usuarioApp.forms import HORAS_DISPONIBLES
from usuarioApp.models import Reserva
from usuarioApp.roles import obtener_rol


class TokenConRolSerializer(TokenObtainPairSerializer):
    """
    Igual que el serializer estándar de SimpleJWT (usuario + contraseña -> access + refresh),
    pero además informa el ROL del usuario (Administrador, Terapeuta o Cliente).

    Seguridad: un JWT va codificado en base64, NO cifrado, así que cualquiera que lo tenga
    puede leer su contenido. Por eso solo se agregan datos no sensibles (username y rol);
    jamás el correo, la contraseña ni datos personales.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.get_username()
        token['rol'] = obtener_rol(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)          # aquí SimpleJWT verifica usuario y contraseña
        data['rol'] = obtener_rol(self.user)    # el cliente de la API conoce su rol sin decodificar el token
        return data


class PerfilTokenSerializer(serializers.Serializer):
    """Respuesta de GET /api/me/: quién es el usuario autenticado por el token."""
    username = serializers.CharField(help_text='Nombre de usuario con el que inició sesión.')
    nombre = serializers.CharField(help_text='Nombre y apellido.', allow_blank=True)
    rol = serializers.CharField(help_text='Administrador, Terapeuta o Cliente.')



# =====================================================================
# Mantenedor 1: TERAPIAS
# =====================================================================
class TerapiaSerializer(serializers.ModelSerializer):
    """Todos los campos de Terapia son públicos, así que un solo serializer sirve a todos los perfiles."""

    class Meta:
        model = Terapia
        fields = ['id', 'nombre', 'precio', 'duracion', 'descripcion', 'imagen', 'creado']
        read_only_fields = ['id', 'creado']

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError('El nombre de la terapia no puede estar vacío.')
        repetidas = Terapia.objects.filter(nombre__iexact=valor)
        if self.instance:
            repetidas = repetidas.exclude(pk=self.instance.pk)
        if repetidas.exists():
            raise serializers.ValidationError('Ya existe una terapia con ese nombre.')
        return valor

    def validate_precio(self, valor):
        if valor <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return valor


# =====================================================================
# Mantenedor 2: TERAPEUTAS  (serializers DIFERENCIADOS por perfil)
# =====================================================================
class TerapeutaPublicoSerializer(serializers.ModelSerializer):
    """
    Lo que ven Cliente y Terapeuta: solo campos públicos.
    NO incluye correo ni certificado (datos privados del profesional).
    """
    terapias = serializers.SlugRelatedField(many=True, read_only=True, slug_field='nombre')

    class Meta:
        model = Terapeuta
        fields = ['id', 'nombre', 'profesion', 'foto', 'terapias']
        read_only_fields = fields


class TerapeutaAdminSerializer(serializers.ModelSerializer):
    """
    Lo que ve y escribe el Administrador: todos los campos, incluida la información sensible.
    `password` es solo de ESCRITURA: se usa para crear la cuenta de acceso del terapeuta
    y nunca aparece en ninguna respuesta.
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
        return valor

    def validate_correo(self, valor):
        valor = valor.strip().lower()
        if len(valor) > 150:
            raise serializers.ValidationError('El correo es demasiado largo para usarse como usuario (máx. 150).')
        otros = User.objects.filter(username__iexact=valor) | User.objects.filter(email__iexact=valor)
        usuario_propio = usuario_de_terapeuta(self.instance.correo) if self.instance else None
        if usuario_propio:
            otros = otros.exclude(pk=usuario_propio.pk)
        if otros.exists():
            raise serializers.ValidationError('Ya existe una cuenta de usuario con ese correo.')
        return valor

    def validate(self, attrs):
        password = attrs.get('password')
        if self.instance is None and not password:
            raise serializers.ValidationError(
                {'password': 'La contraseña es obligatoria para que el terapeuta pueda iniciar sesión.'})
        if password:
            correo = attrs.get('correo') or (self.instance.correo if self.instance else '')
            try:
                validate_password(password, user=User(username=correo, first_name=attrs.get('nombre', '')))
            except DjangoValidationError as e:
                raise serializers.ValidationError({'password': list(e.messages)})
        return attrs

    def _sincronizar_usuario(self, terapeuta, correo_anterior, password):
        """Mantiene la cuenta de acceso (User, grupo Terapeuta) alineada con la ficha, igual que la web."""
        usuario = usuario_de_terapeuta(correo_anterior) if correo_anterior else None
        if usuario is None and not password:
            return
        usuario = usuario or User()
        usuario.username = terapeuta.correo
        usuario.email = terapeuta.correo
        usuario.first_name = terapeuta.nombre
        if password:
            usuario.set_password(password)
        elif not usuario.pk:
            usuario.set_unusable_password()
        usuario.save()
        usuario.groups.add(Group.objects.get_or_create(name=GRUPO_TERAPEUTA)[0])

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        terapeuta = super().create(validated_data)
        self._sincronizar_usuario(terapeuta, None, password)
        return terapeuta

    @transaction.atomic
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        correo_anterior = instance.correo
        terapeuta = super().update(instance, validated_data)
        self._sincronizar_usuario(terapeuta, correo_anterior, password)
        return terapeuta


# =====================================================================
# Transacción del negocio: RESERVAS
# =====================================================================
class ReservaSerializer(serializers.ModelSerializer):
    """
    Vista de Cliente y Terapeuta. El cliente NO puede elegir el estado ni el dueño de la reserva:
    `estado` es de solo lectura y `usuario` se toma del token (ver ReservaViewSet).
    """
    terapia_nombre = serializers.CharField(source='terapia.nombre', read_only=True)
    terapeuta_nombre = serializers.CharField(source='terapeuta.nombre', read_only=True)

    class Meta:
        model = Reserva
        fields = ['id', 'terapia', 'terapia_nombre', 'terapeuta', 'terapeuta_nombre',
                  'fecha', 'hora', 'estado', 'observaciones', 'creado']
        read_only_fields = ['id', 'estado', 'creado']

    # El dueño de la reserva al validar: el cliente autenticado (o el que indique el admin).
    def _dueno(self, attrs):
        if 'usuario' in attrs:
            return attrs['usuario']
        if self.instance:
            return self.instance.usuario
        request = self.context.get('request')
        return request.user if request else None

    def validate_fecha(self, fecha):
        cambia = not self.instance or fecha != self.instance.fecha
        if cambia and fecha < timezone.localdate():
            raise serializers.ValidationError('No puedes agendar una cita en una fecha que ya pasó.')
        return fecha

    def validate(self, attrs):
        # Mismas reglas de negocio que ReservaForm de la aplicación web.
        inst = self.instance
        fecha = attrs.get('fecha', inst.fecha if inst else None)
        hora = attrs.get('hora', inst.hora if inst else None)
        terapia = attrs.get('terapia', inst.terapia if inst else None)
        terapeuta = attrs.get('terapeuta', inst.terapeuta if inst else None)
        errores = {}

        if hora and hora.strftime('%H:%M') not in HORAS_DISPONIBLES:
            errores['hora'] = 'Elige una hora dentro del horario de atención (09:00 a 16:00).'

        if terapeuta and terapia and not terapeuta.terapias.filter(pk=terapia.pk).exists():
            errores['terapeuta'] = f'{terapeuta.nombre} no realiza "{terapia.nombre}".'

        if fecha and hora and 'hora' not in errores:
            ahora = timezone.localtime()
            cambia = not inst or fecha != inst.fecha or hora != inst.hora
            if cambia and fecha == ahora.date() and hora <= ahora.time():
                errores['hora'] = 'Esa hora ya pasó. Elige una hora posterior a la actual.'
            else:
                ocupadas = Reserva.objects.filter(fecha=fecha, hora=hora).exclude(estado='CANCELADA')
                if inst:
                    ocupadas = ocupadas.exclude(pk=inst.pk)
                dueno = self._dueno(attrs)
                if terapeuta and ocupadas.filter(terapeuta=terapeuta).exists():
                    errores['hora'] = f'{terapeuta.nombre} ya tiene una cita en ese horario.'
                elif dueno and ocupadas.filter(usuario=dueno).exists():
                    errores['hora'] = 'El cliente ya tiene otra cita en ese mismo horario.'

        if errores:
            raise serializers.ValidationError(errores)
        return attrs


class ReservaAdminSerializer(ReservaSerializer):
    """Vista del Administrador: además puede indicar el cliente y cambiar el estado (confirmar/cancelar)."""
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta(ReservaSerializer.Meta):
        fields = ['id', 'usuario', 'usuario_username'] + [
            f for f in ReservaSerializer.Meta.fields if f != 'id']
        read_only_fields = ['id', 'creado']
