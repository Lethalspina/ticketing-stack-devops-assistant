from django.urls import path
from . import views
app_name = "tickets"
urlpatterns = [
    path("", views.ticket_list, name="list"),
    path("new/", views.ticket_create, name="create"),
    path("<int:pk>/", views.ticket_detail, name="detail"),
    path("admin/<int:pk>/", views.admin_ticket_detail, name="admin_detail"),
    path("admin/<int:pk>/approve/", views.ticket_approve, name="approve"),
]
