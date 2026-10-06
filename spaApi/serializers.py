#ESTE ARCHIVO SIRVE PARA DEFINIR SERIALIZADORES DE DATOS DE LA API REST
#LOS SERIALIZADORES SON CLASES QUE CONVIERTEN OBJETOS DE PYTHON (MODELOS DE DJANGO) EN JSON Y VICEVERSA, VALIDANDO LOS DATOS RECIBIDOS.
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from adminApp.forms import GRUPO_TERAPEUTA, usuario_de_terapeuta
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta

from usuarioApp.forms import HORAS_DISPONIBLES
from usuarioApp.models import Reserva
from usuarioApp.roles import CLIENTE, obtener_rol


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

# =====================================================================
# Reservas (la transacción del negocio)
# =====================================================================
class ReservaSerializer(serializers.ModelSerializer):
    """
    Reserva vista por un Cliente (o un Terapeuta): el dueño es siempre quien llama,
    y el estado lo maneja el sistema (solo lectura).
    """
    terapia_nombre = serializers.CharField(source='terapia.nombre', read_only=True)
    terapeuta_nombre = serializers.CharField(source='terapeuta.nombre', read_only=True)

    class Meta:
        model = Reserva
        fields = ['id', 'terapia', 'terapia_nombre', 'terapeuta', 'terapeuta_nombre',
                  'fecha', 'hora', 'estado', 'observaciones', 'creado']
        read_only_fields = ['id', 'estado', 'creado']

    def validate_fecha(self, fecha):
        cambia = self.instance is None or fecha != self.instance.fecha
        if cambia and fecha < timezone.localdate():
            raise serializers.ValidationError('No puedes agendar una cita en una fecha que ya pasó.')
        return fecha

    def _dueno(self, datos):
        """A nombre de quién queda la reserva (el Administrador puede elegirlo; el Cliente no)."""
        if datos.get('usuario'):
            return datos['usuario']
        if self.instance:
            return self.instance.usuario
        return self.context['request'].user

    def validate(self, datos):
        # Se revisa lo que llega y lo que cambia: modificar solo las observaciones no vuelve
        # a exigir un horario libre, pero cambiar la hora sí.
        reserva = self.instance

        def valor(campo):
            if campo in datos:
                return datos[campo]
            return getattr(reserva, campo) if reserva else None

        def cambia(*campos):
            return reserva is None or any(c in datos and datos[c] != getattr(reserva, c) for c in campos)

        fecha, hora = valor('fecha'), valor('hora')
        terapia, terapeuta = valor('terapia'), valor('terapeuta')

        # 1) Horario de atención: sesiones de 1 hora, de 09:00 a 16:00 (terminan a las 17:00)
        if 'hora' in datos and hora.strftime('%H:%M') not in HORAS_DISPONIBLES:
            raise serializers.ValidationError(
                {'hora': 'Elige una hora dentro del horario de atención (9:00 a 17:00, en horas exactas).'})

        # 2) El terapeuta debe realizar esa terapia
        if cambia('terapia', 'terapeuta') and not terapeuta.terapias.filter(pk=terapia.pk).exists():
            raise serializers.ValidationError(
                {'terapeuta': f'{terapeuta.nombre} no realiza "{terapia.nombre}". Elige otro terapeuta u otra terapia.'})

        # 3) Si es hoy, la hora no puede haber pasado
        ahora = timezone.localtime()
        if cambia('fecha', 'hora') and fecha == ahora.date() and hora <= ahora.time():
            raise serializers.ValidationError({'hora': 'Esa hora ya pasó. Elige una hora posterior a la actual.'})

        # 4) Sin choques de horario (una reserva cancelada libera el horario)
        if cambia('fecha', 'hora', 'terapeuta'):
            ocupadas = Reserva.objects.filter(fecha=fecha, hora=hora).exclude(estado='CANCELADA')
            if reserva:
                ocupadas = ocupadas.exclude(pk=reserva.pk)
            if ocupadas.filter(terapeuta=terapeuta).exists():
                raise serializers.ValidationError(
                    {'hora': f'{terapeuta.nombre} ya tiene una cita en ese horario. Elige otra hora u otro terapeuta.'})
            if ocupadas.filter(usuario=self._dueno(datos)).exists():
                raise serializers.ValidationError({'hora': 'El cliente ya tiene otra cita en ese mismo horario.'})
        return datos


class ReservaAdminSerializer(ReservaSerializer): 
    """Lo que ve y escribe el Administrador: elige el cliente y puede cambiar el estado."""
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta(ReservaSerializer.Meta):
        fields = ['id', 'usuario', 'usuario_username'] + [f for f in ReservaSerializer.Meta.fields if f != 'id']
        read_only_fields = ['id', 'creado']          # aquí `estado` SÍ se puede escribir

    def validate_usuario(self, usuario):
        # Misma regla que la web: Administrador y Terapeuta no agendan citas, solo los Clientes.
        if obtener_rol(usuario) != CLIENTE:
            raise serializers.ValidationError('Solo se pueden registrar reservas a nombre de usuarios con perfil Cliente.')
        if not usuario.is_active:
            raise serializers.ValidationError('La cuenta de ese cliente está desactivada.')
        return usuario

class TokenConRolSerializer(TokenObtainPairSerializer):
    """Login: entrega access y refresh, y además el rol, para que quien consume la API sepa qué puede hacer."""

    def validate(self, attrs):
        datos = super().validate(attrs)
        datos['rol'] = obtener_rol(self.user)
        return datos