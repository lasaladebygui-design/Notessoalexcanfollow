import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Category(models.Model):
    """Categoría/carpeta de cada usuario -- una sola jerarquía para las
    dos cosas (spec pedía "categorías, carpetas y etiquetas" como tres
    conceptos, pero categoría y carpeta son la misma idea -- agrupar por
    un único sitio -- así que es una sola cosa; las etiquetas sí son
    aparte porque una nota puede llevar varias a la vez)."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="note_categories")
    name = models.CharField("nombre", max_length=60)
    color = models.CharField("color", max_length=7, default="#2DD4BF", help_text="Hex, ej. #2DD4BF.")
    icon = models.CharField("icono", max_length=8, blank=True, help_text="Un emoji, opcional.")
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="categoria_unica_por_usuario"),
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="note_tags")
    name = models.CharField("nombre", max_length=40)

    class Meta:
        verbose_name = "etiqueta"
        verbose_name_plural = "etiquetas"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="etiqueta_unica_por_usuario"),
        ]

    def __str__(self):
        return self.name


class Priority(models.TextChoices):
    LOW = "low", "Baja"
    MEDIUM = "medium", "Media"
    HIGH = "high", "Alta"
    URGENT = "urgent", "Urgente"


class Note(models.Model):
    """Nota libre -- sin prioridad ni "hecho/pendiente" (eso es de Task);
    si tiene fecha, se sincroniza con Google Calendar igual que Task
    (ver notes/calendar_sync.py)."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="notes")
    title = models.CharField("título", max_length=200)
    body = models.TextField("contenido", blank=True)
    category = models.ForeignKey(Category, verbose_name="categoría", on_delete=models.SET_NULL, null=True, blank=True, related_name="notes")
    tags = models.ManyToManyField(Tag, verbose_name="etiquetas", blank=True, related_name="notes")
    is_pinned = models.BooleanField("fijada", default=False)
    reminder_date = models.DateField("fecha", null=True, blank=True)
    google_event_id = models.CharField("id de evento en Google Calendar", max_length=255, blank=True, editable=False)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    updated_at = models.DateTimeField("última edición", auto_now=True)

    class Meta:
        verbose_name = "nota"
        verbose_name_plural = "notas"
        ordering = ["-is_pinned", "-updated_at"]

    def __str__(self):
        return self.title


class Task(models.Model):
    """Tarea, con subtareas (`parent`), prioridad y fecha límite. Una
    subtarea es una Task más con `parent` puesto -- no hay un modelo
    aparte, así que "convertir una subtarea en tarea normal" es tan
    simple como quitarle el padre."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="tasks")
    parent = models.ForeignKey("self", verbose_name="tarea principal", on_delete=models.CASCADE, null=True, blank=True, related_name="subtasks")
    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción", blank=True)
    category = models.ForeignKey(Category, verbose_name="categoría", on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    tags = models.ManyToManyField(Tag, verbose_name="etiquetas", blank=True, related_name="tasks")
    priority = models.CharField("prioridad", max_length=6, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateField(
        "fecha límite", null=True, blank=True,
        help_text="Si la pones, se sincroniza con tu Google Calendar (si lo tienes conectado) y cuenta como recordatorio.",
    )
    google_event_id = models.CharField("id de evento en Google Calendar", max_length=255, blank=True, editable=False)
    is_done = models.BooleanField("hecha", default=False)
    completed_at = models.DateTimeField("completada", null=True, blank=True)
    order = models.PositiveSmallIntegerField("orden", default=0)
    created_at = models.DateTimeField("creada", auto_now_add=True)
    updated_at = models.DateTimeField("última edición", auto_now=True)

    class Meta:
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        ordering = ["is_done", "order", "due_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return bool(self.due_date and not self.is_done and self.due_date < timezone.localdate())

    @property
    def is_subtask(self):
        return self.parent_id is not None

    def mark_done(self, done=True):
        self.is_done = done
        self.completed_at = timezone.now() if done else None
        self.save(update_fields=["is_done", "completed_at"])


# --- Hábitos ---------------------------------------------------------

class Habit(models.Model):
    """Hábito diario -- se marca como hecho día a día (HabitCheckin, una
    fila por día marcado) en vez de guardar un booleano suelto, para
    poder calcular la racha actual sin más que contar días seguidos
    hacia atrás desde hoy."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="habits")
    title = models.CharField("título", max_length=150)
    category = models.ForeignKey(Category, verbose_name="categoría", on_delete=models.SET_NULL, null=True, blank=True, related_name="habits")
    is_archived = models.BooleanField("archivado", default=False)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "hábito"
        verbose_name_plural = "hábitos"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def done_today(self):
        return self.checkins.filter(date=timezone.localdate()).exists()

    def current_streak(self):
        checked_dates = set(self.checkins.values_list("date", flat=True))
        streak = 0
        day = timezone.localdate()
        # Si hoy todavía no está marcado, la racha se cuenta desde ayer
        # (para no romperla de golpe a medianoche si aún da tiempo hoy).
        if day not in checked_dates:
            day -= timezone.timedelta(days=1)
        while day in checked_dates:
            streak += 1
            day -= timezone.timedelta(days=1)
        return streak


class HabitCheckin(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="checkins")
    date = models.DateField("fecha", default=timezone.localdate)

    class Meta:
        verbose_name = "marca de hábito"
        verbose_name_plural = "marcas de hábito"
        constraints = [
            models.UniqueConstraint(fields=["habit", "date"], name="una_marca_por_habito_y_dia"),
        ]

    def __str__(self):
        return f"{self.habit} · {self.date}"


# --- Objetivos ---------------------------------------------------------

class GoalCategory(models.TextChoices):
    HEALTH = "health", "💪 Salud"
    WORK = "work", "💼 Trabajo"
    STUDY = "study", "📚 Estudios"
    FINANCE = "finance", "💰 Finanzas"
    PERSONAL = "personal", "🌱 Personal"
    OTHER = "other", "📌 Otro"


class Goal(models.Model):
    """Objetivo personal, dividido en pasos (GoalStep) -- el progreso es
    siempre "pasos hechos / pasos totales", no un número puesto a mano,
    así que no se puede desincronizar de la lista de pasos real."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="goals")
    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción", blank=True)
    category = models.CharField("categoría", max_length=10, choices=GoalCategory.choices, default=GoalCategory.OTHER)
    target_date = models.DateField("fecha objetivo", null=True, blank=True)
    is_achieved = models.BooleanField("conseguido", default=False)
    achieved_at = models.DateTimeField("conseguido el", null=True, blank=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "objetivo"
        verbose_name_plural = "objetivos"
        ordering = ["is_achieved", "target_date", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def progress_pct(self):
        total = self.steps.count()
        if not total:
            return 100 if self.is_achieved else 0
        done = self.steps.filter(is_done=True).count()
        return round(done / total * 100)

    def mark_achieved(self, achieved=True):
        self.is_achieved = achieved
        self.achieved_at = timezone.now() if achieved else None
        self.save(update_fields=["is_achieved", "achieved_at"])


class GoalStep(models.Model):
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="steps")
    title = models.CharField("título", max_length=200)
    is_done = models.BooleanField("hecho", default=False)
    order = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "paso de objetivo"
        verbose_name_plural = "pasos de objetivo"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


# --- Apuntes de la uni ---------------------------------------------------

class Subject(models.Model):
    """Asignatura de la carrera -- cada una tiene su propio color para
    diferenciarlas de un vistazo, igual que Category."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField("nombre", max_length=100)
    color = models.CharField("color", max_length=7, default="#7c6bf0", help_text="Hex, ej. #7c6bf0.")
    icon = models.CharField("icono", max_length=8, blank=True, default="📘")
    is_shared = models.BooleanField("compartida", default=False)
    share_token = models.UUIDField("token para compartir", default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = "asignatura"
        verbose_name_plural = "asignaturas"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="asignatura_unica_por_usuario"),
        ]

    def __str__(self):
        return self.name


class LectureNote(models.Model):
    """Apunte de una clase concreta de una asignatura -- lo que se ha
    dicho/explicado ese día. `title` es opcional (p.ej. "Tema 4: Derivadas");
    si se deja en blanco se usa la fecha para identificar el apunte."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="lecture_notes")
    date = models.DateField("fecha", default=timezone.localdate)
    title = models.CharField("título", max_length=200, blank=True)
    content = models.TextField("contenido", blank=True)
    # El PDF se guarda como bytes en la propia base de datos (Neon/Postgres)
    # en vez de en el disco de Render -- ese disco es efímero (se borra en
    # cada redeploy, causa real de que un PDF ya subido diera 404 después),
    # y montar un storage de archivos aparte (S3/Supabase Storage) es más
    # infraestructura de la que hace falta para el volumen de esta app.
    pdf_data = models.BinaryField("PDF", null=True, blank=True, editable=False)
    pdf_filename = models.CharField("nombre del PDF", max_length=255, blank=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("última edición", auto_now=True)

    class Meta:
        verbose_name = "apunte de clase"
        verbose_name_plural = "apuntes de clase"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return self.title or f"{self.subject} · {self.date}"


class Event(models.Model):
    """Evento de calendario propiamente dicho -- a diferencia de una Task
    (que tiene fecha límite pero es ante todo "algo por hacer") o una Note
    (recordatorio suelto), un Event es una cita con hora: una reunión, una
    quedada, una clase puntual. Comparte `category` con el resto de la app
    para heredar su color en el calendario sin inventar un sistema de
    colores aparte."""

    user = models.ForeignKey(User, verbose_name="usuario", on_delete=models.CASCADE, related_name="events")
    title = models.CharField("título", max_length=200)
    description = models.TextField("descripción", blank=True)
    date = models.DateField("fecha")
    start_time = models.TimeField("hora de inicio", null=True, blank=True)
    end_time = models.TimeField("hora de fin", null=True, blank=True)
    category = models.ForeignKey(Category, verbose_name="categoría", on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    google_event_id = models.CharField("id de evento en Google Calendar", max_length=255, blank=True, editable=False)
    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("última edición", auto_now=True)

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ["date", "start_time"]

    def __str__(self):
        return self.title
