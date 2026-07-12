from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Ticket
from .forms import TicketForm
from .tasks import procesa_ticket

@login_required
def ticket_list(request):
    tickets = Ticket.objects.filter(creador=request.user).order_by('-creado')[cite: 1]
    return render(request, 'tickets/list.html', {'tickets': tickets})[cite: 1]

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)[cite: 1]
            t.creador = request.user[cite: 1]
            t.save()[cite: 1]
            procesa_ticket.delay(t.id) # Lanzamos asíncronamente a Celery
            return redirect('tickets:detail', pk=t.pk)[cite: 1]
    else:
        form = TicketForm()
    return render(request, 'tickets/create.html', {'form': form})[cite: 1]

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, creador=request.user)[cite: 1]
    return render(request, 'tickets/detail.html', {'ticket': ticket})[cite: 1]