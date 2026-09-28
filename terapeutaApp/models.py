from django.db import models
from django.utils import timezone

class Terapeuta(models.Model):
    nombre = models.CharField(max_length=100)
    profesion = models.CharField(max_length=150)
    correo = models.EmailField(unique=True)
    foto = models.ImageField(upload_to="terapeutas/fotos/", null=True, blank=True)
    certificado = models.FileField(upload_to="terapeutas/certificados/", null=True, blank=True)

    def __str__(self):
        return self.nombre