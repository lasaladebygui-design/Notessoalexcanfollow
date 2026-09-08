from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("registro/", views.signup, name="signup"),

    path("google-calendar/conectar/", views.google_calendar_connect, name="google-calendar-connect"),
    path("google-calendar/callback/", views.google_calendar_callback, name="google-calendar-callback"),
    path("google-calendar/desconectar/", views.google_calendar_disconnect, name="google-calendar-disconnect"),
]
