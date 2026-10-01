from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from .models import Terapia
from terapeutaApp.models import Terapeuta


class TerapiaForm(forms.ModelForm):
    class Meta:
        model = Terapia
        fields = ['nombre', 'precio', 'duracion', 'descripcion', 'imagen']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Masaje descontracturante',
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Precio en pesos',
            }),
            'duracion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 60 minutos',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe brevemente en qué consiste la terapia...',
            }),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise forms.ValidationError('El nombre de la terapia no puede estar vacío.')
        return nombre

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        if precio is not None and precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        return precio


GRUPO_TERAPEUTA = 'Terapeuta'


def usuario_de_terapeuta(correo):
    """
    Devuelve la cuenta de acceso (User) de un terapeuta a partir de su correo.
    Solo considera usuarios del grupo Terapeuta que no sean superusuarios, para
    no tocar por error la cuenta de un administrador o de un cliente.
    """
    if not correo:
        return None
    return (User.objects
            .filter(email__iexact=correo, groups__name=GRUPO_TERAPEUTA, is_superuser=False)
            .first())


class TerapeutaForm(forms.ModelForm):
    """
    Ficha del terapeuta + cuenta de acceso.
    El nombre y apellido se piden por separado en el formulario (mas natural
    para quien lo llena), pero se combinan en el unico campo Terapeuta.nombre
    que ya usa el resto del proyecto (catalogo publico, reservas, etc.), para
    no tener que tocar ningun otro archivo ni modificar el modelo.

    Al guardar se crea (o actualiza) el usuario con el que el terapeuta inicia
    sesion: usuario = correo, contrasena = la ingresada aqui, grupo = Terapeuta.
    """
    nombre_pila = forms.CharField(
        label='Nombre', max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Camila'}),
    )
    apellido = forms.CharField(
        label='Apellido', max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Torres'}),
    )
    password1 = forms.CharField(
        label='Contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    class Meta:
        model = Terapeuta
        # 'nombre' NO va aqui: se arma a partir de nombre_pila + apellido en save()
        fields = ['profesion', 'correo', 'foto', 'certificado']
        widgets = {
            'profesion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Kinesióloga',
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.cl',
            }),
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'certificado': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si se esta editando, buscamos la cuenta actual con el correo anterior
        self.correo_anterior = self.instance.correo if self.instance.pk else None
        self.usuario_existente = usuario_de_terapeuta(self.correo_anterior)

        # Al editar un terapeuta ya existente, separamos su nombre completo
        # guardado (ej: "Camila Torres") en los dos campos del formulario,
        # para que aparezcan precargados.
        if self.instance.pk and self.instance.nombre and not self.initial.get('nombre_pila'):
            partes = self.instance.nombre.strip().split(' ', 1)
            self.initial['nombre_pila'] = partes[0]
            self.initial['apellido'] = partes[1] if len(partes) > 1 else ''

    def clean_nombre_pila(self):
        nombre_pila = self.cleaned_data['nombre_pila'].strip()
        if not nombre_pila:
            raise forms.ValidationError('El nombre no puede estar vacío.')
        return nombre_pila

    def clean_apellido(self):
        apellido = self.cleaned_data['apellido'].strip()
        if not apellido:
            raise forms.ValidationError('El apellido no puede estar vacío.')
        return apellido

    def clean(self):
        cleaned = super().clean()
        correo = (cleaned.get('correo') or '').strip()
        nombre_pila = cleaned.get('nombre_pila', '')
        p1 = cleaned.get('password1', '')
        p2 = cleaned.get('password2', '')
        es_nuevo = not self.instance.pk

        if es_nuevo and not p1:
            self.add_error('password1', 'La contraseña es obligatoria para que el terapeuta pueda iniciar sesión.')

        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            elif correo:
                try:
                    validate_password(p1, user=User(username=correo, first_name=nombre_pila))
                except ValidationError as e:
                    self.add_error('password1', e)

        # El correo se usa como nombre de usuario: no puede estar tomado por otra cuenta
        if correo and (es_nuevo or 'correo' in self.changed_data or p1):
            if len(correo) > 150:
                self.add_error('correo', 'El correo es demasiado largo para usarse como usuario (máx. 150 caracteres).')
            else:
                choque = User.objects.filter(Q(username__iexact=correo) | Q(email__iexact=correo))
                if self.usuario_existente:
                    choque = choque.exclude(pk=self.usuario_existente.pk)
                if choque.exists():
                    self.add_error('correo', 'Ya existe una cuenta de usuario con ese correo.')
        return cleaned

    def save(self, commit=True):
        # Arma el nombre completo que guarda el modelo a partir de los dos
        # campos del formulario, antes de que ModelForm cree/actualice la instancia.
        nombre_pila = self.cleaned_data.get('nombre_pila', '').strip()
        apellido = self.cleaned_data.get('apellido', '').strip()
        self.instance.nombre = f'{nombre_pila} {apellido}'.strip()

        if not commit:
            return super().save(commit=False)

        with transaction.atomic():
            terapeuta = super().save(commit=True)
            self._sincronizar_usuario(terapeuta)
        return terapeuta

    def _sincronizar_usuario(self, terapeuta):
        password = self.cleaned_data.get('password1')
        usuario = self.usuario_existente

        # Ficha antigua sin cuenta y sin contraseña nueva: no se crea usuario
        if usuario is None and not password:
            return
        if usuario is None:
            usuario = User()

        usuario.username = terapeuta.correo
        usuario.email = terapeuta.correo
        usuario.first_name = self.cleaned_data.get('nombre_pila', '').strip()
        usuario.last_name = self.cleaned_data.get('apellido', '').strip()
        if password:
            usuario.set_password(password)
        elif not usuario.pk:
            usuario.set_unusable_password()
        usuario.save()

        grupo, _ = Group.objects.get_or_create(name=GRUPO_TERAPEUTA)
        usuario.groups.add(grupo)


class ClienteForm(forms.ModelForm):
    """
    Edita los datos basicos de un cliente (User) desde el panel admin.
    Los campos de contrasena son opcionales: si se dejan en blanco, la
    contrasena actual del cliente no se modifica. Si se completan, deben
    coincidir y cumplir las reglas de seguridad de Django.
    """
    password1 = forms.CharField(
        label='Nueva contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
        help_text='Déjalo en blanco para mantener la contraseña actual del cliente.',
    )
    password2 = forms.CharField(
        label='Confirmar nueva contraseña', required=False, strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
            'is_active': 'Cuenta activa (puede iniciar sesión)',
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe otra cuenta con este correo.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1', '')
        p2 = cleaned.get('password2', '')

        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(p1, user=self.instance)
                except ValidationError as e:
                    self.add_error('password1', e)
        return cleaned

    def save(self, commit=True):
        usuario = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
        return usuario