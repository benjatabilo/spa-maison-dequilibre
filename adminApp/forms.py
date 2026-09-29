from django import forms
from .models import Terapia


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