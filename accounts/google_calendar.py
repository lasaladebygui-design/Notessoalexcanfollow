"""Integración real (OAuth) con Google Calendar: cada usuario conecta su
propia cuenta una vez y, a partir de ahí, los eventos del calendario de
estrenos de Top Secret se crean solos en su Google Calendar. Sin librerías
de Google (google-api-python-client es muy pesada para lo poco que hace
falta aquí) — solo peticiones HTTP directas a los endpoints de OAuth2 y de
la API de Calendar, con `requests` (ya es dependencia del proyecto).

Si GOOGLE_OAUTH_CLIENT_ID/SECRET no están configuradas, `google_calendar_
enabled()` es False y nada de esto se usa — el resto del sitio (incluido el
calendario en sí, con su botón .ics) sigue funcionando igual."""

from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
SCOPE = "https://www.googleapis.com/auth/calendar.events"
REQUEST_TIMEOUT = 10


def google_calendar_enabled():
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def get_authorization_url(redirect_uri, state):
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code, redirect_uri):
    response = requests.post(TOKEN_URL, data={
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _access_token_for(connection):
    """Reutiliza el access_token guardado si todavía no ha caducado;
    si no, pide uno nuevo con el refresh_token (que ese sí no caduca,
    salvo que el usuario revoque el acceso desde su cuenta de Google)."""
    margin = timedelta(seconds=30)
    if (
        connection.access_token
        and connection.access_token_expires_at
        and connection.access_token_expires_at > timezone.now() + margin
    ):
        return connection.access_token

    response = requests.post(TOKEN_URL, data={
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "refresh_token": connection.refresh_token,
        "grant_type": "refresh_token",
    }, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    connection.access_token = data["access_token"]
    connection.access_token_expires_at = timezone.now() + timedelta(seconds=data.get("expires_in", 3600))
    connection.save(update_fields=["access_token", "access_token_expires_at"])
    return connection.access_token


def create_event(connection, title, date, description=""):
    """Crea un evento de día completo en el Google Calendar del usuario
    conectado y devuelve el id que Google le asigna (para poder borrarlo
    luego si el evento se quita del sitio)."""
    token = _access_token_for(connection)
    body = {
        "summary": title,
        "description": description,
        "start": {"date": date.isoformat()},
        "end": {"date": (date + timedelta(days=1)).isoformat()},
    }
    response = requests.post(
        EVENTS_URL, json=body,
        headers={"Authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["id"]


def delete_event(connection, google_event_id):
    token = _access_token_for(connection)
    response = requests.delete(
        f"{EVENTS_URL}/{google_event_id}",
        headers={"Authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT,
    )
    if response.status_code not in (200, 204, 404, 410):
        response.raise_for_status()
