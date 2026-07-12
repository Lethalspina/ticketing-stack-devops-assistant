from django.conf import settings
from django.db import models

class Ticket(models.Model):
    ESTADOS = [
        ('open',     'Abierto'),
        ('running',  'En curso'),
        ('pending',  'Pendiente de Aprobación'), # <-- NUEVO ESTADO AÑADIDO
        ('resolved', 'Resuelto'),
        ('failed',   'Fallido'),
    ]

    titulo         = models.CharField(max_length=120)
    descripcion    = models.TextField()
    creador        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    estado         = models.CharField(max_length=10, choices=ESTADOS, default='open')
    solucion       = models.TextField(blank=True)
    playbook_usado = models.CharField(max_length=120, blank=True)
    
    # --- NUEVOS CAMPOS PARA HUMAN-IN-THE-LOOP ---
    requiere_aprobacion   = models.BooleanField(default=False)
    target_host_inferido  = models.CharField(max_length=100, blank=True)
    service_name_inferido = models.CharField(max_length=100, blank=True)
    # --------------------------------------------
    
    creado         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.id}] {self.titulo}"