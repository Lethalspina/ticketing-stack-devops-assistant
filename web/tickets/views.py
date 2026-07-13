import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import connection, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from .forms import TicketForm
from .models import Ticket
from .tasks import analyze_ticket, execute_playbook

@require_GET
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})

@login_required
def ticket_list(request):
    from django.core.paginator import Paginator
    paginator = Paginator(Ticket.objects.filter(creator=request.user), 10)
    return render(request, "tickets/list.html", {"page_obj": paginator.get_page(request.GET.get("page"))})

@login_required
def ticket_create(request):
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            ticket = form.save(commit=False)
            ticket.creator = request.user
            ticket.save()
            transaction.on_commit(lambda: analyze_ticket.apply_async(args=[ticket.pk], queue="analysis"))
        messages.success(request, "Ticket creado y enviado para análisis.")
        return redirect("tickets:detail", pk=ticket.pk)
    return render(request, "tickets/create.html", {"form": form})

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, creator=request.user)
    return render(request, "tickets/detail.html", {"ticket": ticket})

@require_POST
@login_required
@permission_required("tickets.can_approve_automation", raise_exception=True)
def ticket_approve(request, pk):
    with transaction.atomic():
        ticket = get_object_or_404(Ticket.objects.select_for_update(), pk=pk)
        if ticket.status != Ticket.Status.PENDING or not ticket.proposal_version:
            messages.error(request, "El ticket ya no está pendiente o la propuesta no es válida.")
            return redirect("tickets:admin_detail", pk=ticket.pk)
        ticket.approved_by = request.user
        ticket.approved_at = timezone.now()
        ticket.execution_token = uuid.uuid4()
        ticket.status = Ticket.Status.QUEUED
        token = str(ticket.execution_token)
        ticket.save(update_fields=["approved_by", "approved_at", "execution_token", "status", "updated_at"])
        transaction.on_commit(lambda: execute_playbook.apply_async(args=[ticket.pk, token], queue="automation"))
    messages.success(request, "Automatización aprobada y enviada a la cola.")
    return redirect("tickets:admin_detail", pk=ticket.pk)

@login_required
@permission_required("tickets.can_approve_automation", raise_exception=True)
def admin_ticket_detail(request, pk):
    return render(request, "tickets/detail.html", {"ticket": get_object_or_404(Ticket, pk=pk), "admin_view": True})
