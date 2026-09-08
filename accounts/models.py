from django.conf import settings
from django.db import models


class GoogleCalendarConnection(models.Model):
    """Conexión OAuth de un usuario con su Google Calendar: guarda el
    refresh_token que Google entrega al conceder el permiso, que no
    caduca salvo que el usuario lo revoque desde su cuenta de Google. El
    access_token sí caduca (normalmente en 1h) y se renueva solo con el
    refresh_token cuando hace falta (ver google_calendar.py)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="google_calendar_connection")
    refresh_token = models.CharField("refresh token", max_length=255)
    access_token = models.CharField("access token", max_length=255, blank=True)
    access_token_expires_at = models.DateTimeField("caduca", null=True, blank=True)
    connected_at = models.DateTimeField("conectado", auto_now_add=True)

    class Meta:
        verbose_name = "conexión con Google Calendar"
        verbose_name_plural = "conexiones con Google Calendar"

    def __str__(self):
        return f"Google Calendar de {self.user}"
