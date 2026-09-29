from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Reserva
from django.core.exceptions import ValidationError
from django.utils import timezone

class ReservaForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user  # cliente autenticado, para validar sus propios choques de horario

    class Meta:
        model = Reserva
        fields = ['terapia', 'terapeuta', 'fecha', 'hora', 'observaciones']
        widgets = {
            'terapia': forms.Select(attrs={'class': 'form-select'}),
            'terapeuta': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escribe aquí cualquier indicación o preferencia para tu cita...'
            }),
        }

    def _es_nueva_o_cambio(self, campo):
        """True si la reserva es nueva o si el usuario modificó ese campo."""
        return not self.instance.pk or campo in self.changed_data

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')
        if fecha and self._es_nueva_o_cambio('fecha') and fecha < timezone.localdate():
            raise ValidationError('No puedes agendar una cita en una fecha que ya pasó.')
        return fecha

    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get('fecha')
        hora = cleaned.get('hora')
        terapeuta = cleaned.get('terapeuta')

        if not (fecha and hora):
            return cleaned

        # 1. Si es hoy, la hora no puede haber pasado
        ahora = timezone.localtime()
        if (fecha == ahora.date() and hora <= ahora.time()
                and (self._es_nueva_o_cambio('hora') or self._es_nueva_o_cambio('fecha'))):
            self.add_error('hora', 'Esa hora ya pasó. Elige una hora posterior a la actual.')
            return cleaned

        # Reservas que ocupan horario (las canceladas lo liberan)
        ocupadas = Reserva.objects.filter(fecha=fecha, hora=hora).exclude(estado='CANCELADA')
        if self.instance.pk:
            ocupadas = ocupadas.exclude(pk=self.instance.pk)

        # 2. El terapeuta no puede tener dos citas a la misma hora
        if terapeuta and ocupadas.filter(terapeuta=terapeuta).exists():
            self.add_error(
                'hora',
                f'{terapeuta.nombre} ya tiene una cita en ese horario. Elige otra hora u otro terapeuta.'
            )

        # 3. El cliente no puede tener dos citas a la misma hora
        elif self.user and ocupadas.filter(usuario=self.user).exists():
            self.add_error('hora', 'Ya tienes otra cita agendada en ese mismo horario.')

        return cleaned


class PerfilUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class RegistroForm(UserCreationForm):
    first_name = forms.CharField(
        label='Nombre', max_length=150, required=True
    )
    last_name = forms.CharField(
        label='Apellido', max_length=150, required=True
    )
    email = forms.EmailField(
        label='Correo electrónico', required=True
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {'username': 'Nombre de usuario'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplica estilo Bootstrap a todos los campos
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Repetir contraseña'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email