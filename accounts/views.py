import secrets

import requests
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import SignupForm
from .google_calendar import exchange_code_for_tokens, get_authorization_url, google_calendar_enabled
from .models import GoogleCalendarConnection

GOOGLE_OAUTH_STATE_SESSION_KEY = "google_oauth_state"


def signup(request):
    if request.user.is_authenticated:
        return redirect("notes:dashboard")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("notes:dashboard")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def google_calendar_connect(request):
    if not google_calendar_enabled():
        raise Http404
    state = secrets.token_urlsafe(16)
    request.session[GOOGLE_OAUTH_STATE_SESSION_KEY] = state
    redirect_uri = request.build_absolute_uri(reverse("accounts:google-calendar-callback"))
    return redirect(get_authorization_url(redirect_uri, state))


@login_required
def google_calendar_callback(request):
    if not google_calendar_enabled():
        raise Http404

    expected_state = request.session.pop(GOOGLE_OAUTH_STATE_SESSION_KEY, None)
    state = request.GET.get("state")
    if not state or state != expected_state:
        messages.error(request, "No se pudo verificar la conexión con Google. Inténtalo de nuevo.")
        return redirect("notes:calendar")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google no autorizó la conexión.")
        return redirect("notes:calendar")

    redirect_uri = request.build_absolute_uri(reverse("accounts:google-calendar-callback"))
    try:
        tokens = exchange_code_for_tokens(code, redirect_uri)
    except requests.RequestException:
        messages.error(request, "No se pudo conectar con Google Calendar. Inténtalo de nuevo.")
        return redirect("notes:calendar")

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        messages.error(request, "Google no devolvió los permisos esperados (prueba a desconectar el acceso desde tu cuenta de Google y vuelve a intentarlo).")
        return redirect("notes:calendar")

    GoogleCalendarConnection.objects.update_or_create(
        user=request.user,
        defaults={
            "refresh_token": refresh_token,
            "access_token": tokens.get("access_token", ""),
            "access_token_expires_at": timezone.now() + timezone.timedelta(seconds=tokens.get("expires_in", 3600)),
        },
    )
    messages.success(request, "Google Calendar conectado. Las notas y tareas con fecha se crearán solas en tu calendario a partir de ahora.")
    return redirect("notes:calendar")


@login_required
@require_POST
def google_calendar_disconnect(request):
    GoogleCalendarConnection.objects.filter(user=request.user).delete()
    from notes.models import Note, Task

    Note.objects.filter(user=request.user).exclude(google_event_id="").update(google_event_id="")
    Task.objects.filter(user=request.user).exclude(google_event_id="").update(google_event_id="")
    messages.info(request, "Google Calendar desconectado.")
    return redirect("notes:calendar")
