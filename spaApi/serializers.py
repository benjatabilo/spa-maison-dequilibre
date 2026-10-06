#ESTE ARCHIVO SIRVE PARA DEFINIR SERIALIZADORES DE DATOS DE LA API REST
#LOS SERIALIZADORES SON CLASES QUE CONVIERTEN OBJETOS DE PYTHON (MODELOS DE DJANGO) EN JSON Y VICEVERSA, VALIDANDO LOS DATOS RECIBIDOS.
from rest_framework import serializers

from adminApp.models import Terapia


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