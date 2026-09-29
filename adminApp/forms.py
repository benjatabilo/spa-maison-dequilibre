from django import forms
from django.contrib.auth.models import User
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


class TerapeutaForm(forms.ModelForm):
    class Meta:
        model = Terapeuta
        fields = ['nombre', 'profesion', 'correo', 'foto', 'certificado']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Camila Torres',
            }),
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

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise forms.ValidationError('El nombre del terapeuta no puede estar vacío.')
        return nombre


class ClienteForm(forms.ModelForm):
    """Edita los datos basicos de un cliente (User) desde el panel admin."""
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