from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuenta/", include("accounts.urls")),
    path("", include("notes.urls")),
]

# Nada en la app usa FileField/ImageField ahora mismo -- el PDF de los
# apuntes se guarda como bytes en la base de datos (ver LectureNote.pdf_data)
# precisamente porque el disco de Render es efímero. Este bloque queda por
# si algún día hace falta subir algo a disco en local; en producción no se
# activa (y no haría falta, dado lo anterior).
if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
