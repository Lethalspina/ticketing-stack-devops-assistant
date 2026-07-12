from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.ticket_list, name='list'),[cite: 1]
    path('new/', views.ticket_create, name='create'),[cite: 1]
    path('<int:pk>/', views.ticket_detail, name='detail'),[cite: 1]
]