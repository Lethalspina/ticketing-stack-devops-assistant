from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction # MEJORA: Importamos el módulo de transacciones
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Ticket
from .forms import TicketForm
from .tasks import analizar_ticket, ejecutar_playbook

@login_required
def ticket_list(request):
    # Obtenemos el QuerySet de todos los tickets
    tickets_list = Ticket.objects.filter(creador=request.user).order_by('-creado')
    
    # Creamos un paginador con 10 tickets por página
    paginator = Paginator(tickets_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Pasamos el objeto paginado al template en lugar de toda la lista
    return render(request, 'tickets/list.html', {'page_obj': page_obj})

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.creador = request.user
            t.save()
            
            # MEJORA: Se encola la tarea asíncrona SOLO cuando la transacción de la BD se consolide (commit)
            transaction.on_commit(lambda: analizar_ticket.delay(t.id)) 

            return redirect('tickets:detail', pk=t.pk)
    else:
        form = TicketForm()
    return render(request, 'tickets/create.html', {'form': form})

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, creador=request.user)
    return render(request, 'tickets/detail.html', {'ticket': ticket})

@login_required
@user_passes_test(lambda u: u.is_staff) # <-- Solo los miembros del grupo IT_Admins (staff) pueden entrar
def ticket_approve(request, pk):
    # Obtenemos el ticket sin importar quién lo creó (el admin puede ver todos los retenidos)
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST' and ticket.estado == 'pending':
        # Encolamos la Tarea 2 (Ejecución) y le pasamos el relevo a Celery
        ejecutar_playbook.delay(ticket.id)
        messages.success(request, f"¡Ejecución aprobada! Iniciando {ticket.playbook_usado}.yml en {ticket.target_host_inferido}...")
        
    return redirect('tickets:detail', pk=ticket.pk)