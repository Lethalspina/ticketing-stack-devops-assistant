from django.contrib import admin
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "creator", "status", "created_at", "approved_by")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "creator__username")
    readonly_fields = ("proposal_version", "execution_token", "approved_at", "execution_started_at", "execution_finished_at", "result_code", "result_stdout", "error_message")
