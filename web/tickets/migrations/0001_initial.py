import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="Ticket", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("title", models.CharField(max_length=200, verbose_name="título")),
        ("description", models.TextField(max_length=5000, verbose_name="descripción")),
        ("status", models.CharField(choices=[("open","Abierto"),("analyzing","Analizando"),("pending","Pendiente de aprobación"),("queued","En cola"),("running","En ejecución"),("resolved","Resuelto"),("failed","Fallido"),("rejected","Rechazado")], db_index=True, default="open", max_length=16)),
        ("proposed_playbook", models.CharField(blank=True, max_length=32)),
        ("proposed_target_id", models.CharField(blank=True, max_length=64)),
        ("proposed_service_id", models.CharField(blank=True, max_length=64)),
        ("proposal_reason", models.TextField(blank=True, max_length=1000)),
        ("proposal_version", models.UUIDField(blank=True, editable=False, null=True)),
        ("approved_at", models.DateTimeField(blank=True, null=True)),
        ("execution_token", models.UUIDField(blank=True, editable=False, null=True, unique=True)),
        ("execution_started_at", models.DateTimeField(blank=True, null=True)),
        ("execution_finished_at", models.DateTimeField(blank=True, null=True)),
        ("result_code", models.IntegerField(blank=True, null=True)),
        ("result_stdout", models.TextField(blank=True)),
        ("result_stderr", models.TextField(blank=True)),
        ("error_message", models.TextField(blank=True, max_length=2000)),
        ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
        ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_tickets", to=settings.AUTH_USER_MODEL)),
        ("creator", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tickets", to=settings.AUTH_USER_MODEL)),
    ], options={"ordering":["-created_at"], "permissions":[("can_approve_automation","Puede aprobar automatizaciones críticas")]}),
    migrations.AddIndex(model_name="ticket", index=models.Index(fields=["creator", "-created_at"], name="tickets_tic_creator_idx")),
    ]
