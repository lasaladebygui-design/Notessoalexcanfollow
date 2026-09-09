from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve


def media_serve(request, path):
    # No pasa document_root=settings.MEDIA_ROOT como kwarg fijo del
    # urlpattern porque eso lo capturaría una sola vez, al cargar este
    # módulo -- leerlo aquí dentro asegura que siempre se usa el
    # settings.MEDIA_ROOT actual (importa sobre todo en tests, que lo
    # cambian con override_settings).
    return serve(request, path, document_root=settings.MEDIA_ROOT)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuenta/", include("accounts.urls")),
    path("", include("notes.urls")),
    # Sirve MEDIA_URL tanto en DEBUG como en producción -- antes solo se
    # servía en local (vía el atajo static(), que es DEBUG-only), así que
    # un PDF recién subido daba 404 en Render. No es lo más eficiente para
    # mucho tráfico, pero para el uso personal de esta app es correcto y
    # evita depender de un storage aparte.
    path("media/<path:path>", media_serve),
]
