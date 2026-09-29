from django.db import models
from django.utils import timezone

class Terapia(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.PositiveIntegerField()
    duracion = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to="terapias/", null=True, blank=True)
    creado = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.nombre