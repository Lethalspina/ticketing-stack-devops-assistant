from django.conf import settings
from django.db import models

class Ticket(models.Model):
    ESTADOS = [
        ('open',     'Abierto'),
        ('running',  'En curso'),
        ('resolved', 'Resuelto'),
        ('failed',   'Fallido'),
    ][cite: 1]

    titulo         = models.CharField(max_length=120)[cite: 1]
    descripcion    = models.TextField()[cite: 1]
    creador        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)[cite: 1]
    estado         = models.CharField(max_length=10, choices=ESTADOS, default='open')[cite: 1]
    solucion       = models.TextField(blank=True)[cite: 1]
    playbook_usado = models.CharField(max_length=120, blank=True)[cite: 1]
    creado         = models.DateTimeField(auto_now_add=True)[cite: 1]

    def __str__(self):
        return f"[{self.id}] {self.titulo}"[cite: 1]