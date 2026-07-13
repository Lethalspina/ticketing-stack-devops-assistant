from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from tickets.views import health

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tickets:list", permanent=False)),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("tickets/", include("tickets.urls", namespace="tickets")),
]
