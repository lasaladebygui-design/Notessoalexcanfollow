"""Sincronización con Google Calendar compartida por Note y Task -- misma
idea que el calendario de Top Secret (ver apps/secret/views.py): si
falla la red, no debe impedir guardar la nota/tarea, solo se deja sin
sincronizar para la próxima vez."""
import requests

from accounts.google_calendar import create_event as google_create_event
from accounts.google_calendar import delete_event as google_delete_event
from accounts.google_calendar import google_calendar_enabled


def sync_event(request_user, obj, date_field, old_date):
    """`obj` es una Note o una Task; `date_field` es "reminder_date" o
    "due_date". Crea/borra el evento según haya cambiado la fecha."""
    if not (google_calendar_enabled() and hasattr(request_user, "google_calendar_connection")):
        return
    connection = request_user.google_calendar_connection
    new_date = getattr(obj, date_field)
    date_changed = old_date != new_date

    if obj.google_event_id and (date_changed or not new_date):
        try:
            google_delete_event(connection, obj.google_event_id)
        except requests.RequestException:
            pass
        obj.google_event_id = ""

    if new_date and (date_changed or not obj.google_event_id):
        description = getattr(obj, "body", "") or getattr(obj, "description", "")
        try:
            obj.google_event_id = google_create_event(connection, obj.title, new_date, description=description)
        except requests.RequestException:
            pass

    obj.save(update_fields=["google_event_id"])


def delete_event_for(request_user, obj):
    if obj.google_event_id and hasattr(request_user, "google_calendar_connection"):
        try:
            google_delete_event(request_user.google_calendar_connection, obj.google_event_id)
        except requests.RequestException:
            pass
