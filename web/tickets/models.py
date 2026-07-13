import uuid
from django.conf import settings
from django.db import models

class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Abierto"
        ANALYZING = "analyzing", "Analizando"
        PENDING = "pending", "Pendiente de aprobación"
        QUEUED = "queued", "En cola"
        RUNNING = "running", "En ejecución"
        RESOLVED = "resolved", "Resuelto"
        FAILED = "failed", "Fallido"
        REJECTED = "rejected", "Rechazado"

    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción", max_length=5000)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tickets")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True)
    proposed_playbook = models.CharField(max_length=32, blank=True)
    proposed_target_id = models.CharField(max_length=64, blank=True)
    proposed_service_id = models.CharField(max_length=64, blank=True)
    proposal_reason = models.TextField(blank=True, max_length=1000)
    proposal_version = models.UUIDField(null=True, blank=True, editable=False)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="approved_tickets")
    approved_at = models.DateTimeField(null=True, blank=True)
    execution_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    execution_started_at = models.DateTimeField(null=True, blank=True)
    execution_finished_at = models.DateTimeField(null=True, blank=True)
    result_code = models.IntegerField(null=True, blank=True)
    result_stdout = models.TextField(blank=True)
    result_stderr = models.TextField(blank=True)
    error_message = models.TextField(blank=True, max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("can_approve_automation", "Puede aprobar automatizaciones críticas")]
        indexes = [models.Index(fields=["creator", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def new_proposal_version(self):
        self.proposal_version = uuid.uuid4()
