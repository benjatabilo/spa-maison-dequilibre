from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Importamos las entidades maestras de las otras apps
from adminApp.models import Terapia
from terapeutaApp.models import Terapeuta


class Reserva(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('CANCELADA', 'Cancelada'),
        ('COMPLETADA', 'Completada'),
    ]

    # Relación con el usuario/cliente registrado (para su CRUD personal)
    usuario = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="mis_reservas",
        verbose_name="Cliente / Usuario"
    )
    
    # Relaciones con los dos Mantenedores
    terapia = models.ForeignKey(
        Terapia, 
        on_delete=models.RESTRICT, 
        related_name="reservas",
        verbose_name="Terapia Seleccionada"
    )
    terapeuta = models.ForeignKey(
        Terapeuta, 
        on_delete=models.RESTRICT, 
        related_name="reservas",
        verbose_name="Terapeuta Asignado"
    )
    
    # Datos específicos de la cita
    fecha = models.DateField(verbose_name="Fecha de la Cita")
    hora = models.TimeField(verbose_name="Hora de la Cita")
    estado = models.CharField(
        max_length=20, 
        choices=ESTADOS, 
        default='PENDIENTE', 
        verbose_name="Estado de la Reserva"
    )
    observaciones = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Notas u Observaciones del Cliente"
    )
    creado = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "reservas"
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-fecha", "-hora"]

    def __str__(self):
        return f"Reserva #{self.id} - {self.usuario.username} - {self.terapia.nombre} ({self.fecha})"