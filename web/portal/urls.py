from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),[cite: 1]
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),[cite: 1]
    path('tickets/', include('tickets.urls', namespace='tickets')),[cite: 1]
]