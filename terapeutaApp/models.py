from django.db import models
from django.utils import timezone
from adminApp.models import Terapia

class Terapeuta(models.Model):
    nombre = models.CharField(max_length=100)
    profesion = models.CharField(max_length=150)
    correo = models.EmailField(unique=True, max_length=191)
    foto = models.ImageField(upload_to="terapeutas/fotos/", null=True, blank=True)
    certificado = models.FileField(upload_to="terapeutas/certificados/", null=True, blank=True)
    terapias = models.ManyToManyField(
        Terapia,
        related_name='terapeutas',
        blank=True,
        verbose_name='Terapias que realiza',
    )

    class Meta:
        db_table = 'terapeutas' #esto es para renombrar la tabla en php admin.

    def __str__(self):
        return self.nombre