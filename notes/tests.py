import json
from datetime import timedelta
from itertools import count
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Goal, GoalStep, Habit, LectureNote, Note, Priority, Subject, Tag, Task

_username_counter = count(1)


def make_user(_unused_email=None):
    username = f"tester{next(_username_counter)}"
    user = User.objects.create_user(username=username, password="Testpass123!")
    return user


class NoteCrudTests(TestCase):
    def setUp(self):
        self.user = make_user("notes1@test.local")
        self.other = make_user("notes2@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_crear_nota(self):
        response = self.client.post(reverse("notes:note-create"), {
            "title": "Idea para el finde", "body": "Ver una peli de miedo", "category": "", "tags": [],
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Note.objects.filter(user=self.user, title="Idea para el finde").exists())

    def test_no_se_ven_las_notas_de_otro_usuario(self):
        Note.objects.create(user=self.other, title="Nota ajena")
        Note.objects.create(user=self.user, title="Nota mía")

        response = self.client.get(reverse("notes:note-list"))
        self.assertContains(response, "Nota mía")
        self.assertNotContains(response, "Nota ajena")

    def test_no_se_puede_editar_una_nota_ajena(self):
        note = Note.objects.create(user=self.other, title="Nota ajena")
        response = self.client.get(reverse("notes:note-edit", args=[note.pk]))
        self.assertEqual(response.status_code, 404)

    def test_buscar_por_titulo_o_contenido(self):
        Note.objects.create(user=self.user, title="Receta de lasaña", body="Con bechamel")
        Note.objects.create(user=self.user, title="Otra cosa", body="Nada que ver")

        response = self.client.get(reverse("notes:note-list"), {"q": "bechamel"})
        self.assertContains(response, "Receta de lasaña")
        self.assertNotContains(response, "Otra cosa")

    def test_fijar_nota(self):
        note = Note.objects.create(user=self.user, title="Fijar esto")
        self.client.post(reverse("notes:note-toggle-pin", args=[note.pk]))
        note.refresh_from_db()
        self.assertTrue(note.is_pinned)

    def test_borrar_nota(self):
        note = Note.objects.create(user=self.user, title="Borrar esto")
        self.client.post(reverse("notes:note-delete", args=[note.pk]))
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())


class TaskCrudTests(TestCase):
    def setUp(self):
        self.user = make_user("notes3@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_crear_tarea_con_prioridad_y_fecha(self):
        response = self.client.post(reverse("notes:task-create"), {
            "title": "Pagar el alquiler", "description": "", "category": "",
            "tags": [], "priority": Priority.URGENT, "due_date": "2026-09-15", "parent": "",
        })
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(user=self.user, title="Pagar el alquiler")
        self.assertEqual(task.priority, Priority.URGENT)

    def test_subtarea_se_crea_con_padre(self):
        parent = Task.objects.create(user=self.user, title="Mudanza")
        response = self.client.post(reverse("notes:task-create"), {
            "title": "Cajas", "description": "", "category": "", "tags": [],
            "priority": Priority.MEDIUM, "due_date": "", "parent": parent.pk,
        })
        self.assertEqual(response.status_code, 302)
        subtask = Task.objects.get(title="Cajas")
        self.assertEqual(subtask.parent, parent)
        self.assertTrue(subtask.is_subtask)

    def test_marcar_tarea_como_hecha_registra_fecha(self):
        task = Task.objects.create(user=self.user, title="Test")
        self.client.post(reverse("notes:task-toggle-done", args=[task.pk]))
        task.refresh_from_db()
        self.assertTrue(task.is_done)

    def test_editar_tarea_precarga_la_fecha_en_formato_iso(self):
        # Bug real: el input type="date" del navegador exige "YYYY-MM-DD"
        # en el atributo value, pero con LANGUAGE_CODE="es" Django lo
        # renderizaba en "dd/mm/yyyy" -- el navegador lo descartaba y el
        # campo aparecía vacío al editar una tarea con fecha ya puesta.
        task = Task.objects.create(user=self.user, title="Con fecha", due_date="2026-09-15")
        response = self.client.get(reverse("notes:task-edit", args=[task.pk]))
        self.assertContains(response, 'value="2026-09-15"')

    def test_tarea_vencida_se_detecta(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        task = Task.objects.create(user=self.user, title="Tarde", due_date=yesterday)
        self.assertTrue(task.is_overdue)

    def test_tarea_hecha_no_cuenta_como_vencida(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        task = Task.objects.create(user=self.user, title="Tarde pero hecha", due_date=yesterday, is_done=True)
        self.assertFalse(task.is_overdue)

    def test_lista_de_tareas_solo_ensena_las_principales_no_las_subtareas_sueltas(self):
        parent = Task.objects.create(user=self.user, title="Principal")
        Task.objects.create(user=self.user, title="Secundaria", parent=parent)

        response = self.client.get(reverse("notes:task-list"))
        tasks = list(response.context["tasks"])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0], parent)

    def test_filtro_de_prioridad(self):
        urgent = Task.objects.create(user=self.user, title="Tarea A", priority=Priority.URGENT)
        Task.objects.create(user=self.user, title="Tarea B", priority=Priority.LOW)

        response = self.client.get(reverse("notes:task-list"), {"priority": Priority.URGENT})
        self.assertEqual(list(response.context["tasks"]), [urgent])


class DashboardTests(TestCase):
    def setUp(self):
        self.user = make_user("notes4@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_dashboard_carga_vacio(self):
        response = self.client.get(reverse("notes:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["pending_count"], 0)

    def test_dashboard_cuenta_pendientes_vencidas_y_prioritarias(self):
        today = timezone.localdate()
        Task.objects.create(user=self.user, title="Vencida", due_date=today - timedelta(days=2))
        Task.objects.create(user=self.user, title="Urgente", priority=Priority.URGENT)
        Task.objects.create(user=self.user, title="Hecha", is_done=True, completed_at=timezone.now())

        response = self.client.get(reverse("notes:dashboard"))
        self.assertEqual(response.context["pending_count"], 2)
        self.assertEqual(response.context["overdue_count"], 1)
        self.assertEqual(response.context["high_priority_count"], 1)
        self.assertEqual(response.context["completed_this_week"], 1)

    def test_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse("notes:dashboard"))
        self.assertEqual(response.status_code, 302)


class CategoryAndTagTests(TestCase):
    def setUp(self):
        self.user = make_user("notes5@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_crear_categoria(self):
        self.client.post(reverse("notes:category-list"), {"name": "Trabajo", "color": "#2DD4BF", "icon": "💼"})
        self.assertTrue(Category.objects.filter(user=self.user, name="Trabajo").exists())

    def test_crear_etiqueta(self):
        self.client.post(reverse("notes:tag-create"), {"name": "urgente"})
        self.assertTrue(Tag.objects.filter(user=self.user, name="urgente").exists())

    def test_no_se_duplica_una_etiqueta_repetida(self):
        Tag.objects.create(user=self.user, name="casa")
        self.client.post(reverse("notes:tag-create"), {"name": "casa"})
        self.assertEqual(Tag.objects.filter(user=self.user, name="casa").count(), 1)

    def test_borrar_categoria_no_borra_las_notas(self):
        category = Category.objects.create(user=self.user, name="Temp")
        note = Note.objects.create(user=self.user, title="Nota", category=category)
        self.client.post(reverse("notes:category-delete", args=[category.pk]))
        note.refresh_from_db()
        self.assertIsNone(note.category)


class CalendarSyncTests(TestCase):
    """Igual que el calendario de Top Secret: si falla la red al crear el
    evento, la nota/tarea se guarda igual (ver notes/calendar_sync.py)."""

    def setUp(self):
        self.user = make_user("notes6@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    @patch("notes.calendar_sync.google_calendar_enabled", return_value=False)
    def test_sin_google_calendar_activado_no_intenta_sincronizar(self, mock_enabled):
        response = self.client.post(reverse("notes:task-create"), {
            "title": "Con fecha", "description": "", "category": "", "tags": [],
            "priority": Priority.MEDIUM, "due_date": "2026-10-01", "parent": "",
        })
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(title="Con fecha")
        self.assertEqual(task.google_event_id, "")


class CalendarViewTests(TestCase):
    def setUp(self):
        self.user = make_user("notes7@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_calendario_agrupa_tareas_y_notas_por_dia(self):
        Task.objects.create(user=self.user, title="Tarea con fecha", due_date="2026-09-15")
        Note.objects.create(user=self.user, title="Nota con fecha", reminder_date="2026-09-15")

        response = self.client.get(reverse("notes:calendar"), {"year": 2026, "month": 9})
        weeks = response.context["weeks"]
        day_15 = next(day for week in weeks for day in week if day["date"].day == 15 and day["in_month"])
        self.assertEqual(len(day_15["items"]), 2)

    def test_requiere_login(self):
        self.client.logout()
        response = self.client.get(reverse("notes:calendar"))
        self.assertEqual(response.status_code, 302)


class HabitTests(TestCase):
    def setUp(self):
        self.user = make_user("notes8@test.local")
        self.other = make_user("notes9@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_crear_habito(self):
        response = self.client.post(reverse("notes:habit-list"), {"title": "Beber agua", "category": ""})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Habit.objects.filter(user=self.user, title="Beber agua").exists())

    def test_marcar_y_desmarcar_hoy(self):
        habit = Habit.objects.create(user=self.user, title="Leer")
        self.assertFalse(habit.done_today())

        self.client.post(reverse("notes:habit-toggle-checkin", args=[habit.pk]))
        self.assertTrue(habit.done_today())

        self.client.post(reverse("notes:habit-toggle-checkin", args=[habit.pk]))
        self.assertFalse(habit.done_today())

    def test_racha_cuenta_dias_seguidos_hacia_atras(self):
        habit = Habit.objects.create(user=self.user, title="Meditar")
        today = timezone.localdate()
        for offset in range(3):
            habit.checkins.create(date=today - timedelta(days=offset))
        self.assertEqual(habit.current_streak(), 3)

    def test_no_se_puede_marcar_un_habito_ajeno(self):
        habit = Habit.objects.create(user=self.other, title="Ajeno")
        response = self.client.post(reverse("notes:habit-toggle-checkin", args=[habit.pk]))
        self.assertEqual(response.status_code, 404)


class GoalTests(TestCase):
    def setUp(self):
        self.user = make_user("notes10@test.local")
        self.other = make_user("notes11@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_crear_objetivo(self):
        response = self.client.post(reverse("notes:goal-create"), {
            "title": "Correr una maratón", "description": "", "category": "health", "target_date": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Goal.objects.filter(user=self.user, title="Correr una maratón").exists())

    def test_progreso_sin_pasos(self):
        goal = Goal.objects.create(user=self.user, title="Sin pasos")
        self.assertEqual(goal.progress_pct, 0)
        goal.mark_achieved()
        self.assertEqual(goal.progress_pct, 100)

    def test_progreso_deriva_de_los_pasos(self):
        goal = Goal.objects.create(user=self.user, title="Con pasos")
        step1 = GoalStep.objects.create(goal=goal, title="Paso 1")
        GoalStep.objects.create(goal=goal, title="Paso 2")
        self.assertEqual(goal.progress_pct, 0)

        self.client.post(reverse("notes:goal-step-toggle", args=[step1.pk]))
        self.assertEqual(goal.progress_pct, 50)

    def test_no_se_puede_ver_un_objetivo_ajeno(self):
        goal = Goal.objects.create(user=self.other, title="Ajeno")
        response = self.client.get(reverse("notes:goal-detail", args=[goal.pk]))
        self.assertEqual(response.status_code, 404)

    def test_borrar_paso_ajeno_da_404(self):
        goal = Goal.objects.create(user=self.other, title="Ajeno")
        step = GoalStep.objects.create(goal=goal, title="Paso ajeno")
        response = self.client.post(reverse("notes:goal-step-delete", args=[step.pk]))
        self.assertEqual(response.status_code, 404)


class SearchTests(TestCase):
    def setUp(self):
        self.user = make_user("notes12@test.local")
        self.other = make_user("notes13@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_busca_en_notas_y_tareas_propias(self):
        Note.objects.create(user=self.user, title="Receta de lasaña")
        Task.objects.create(user=self.user, title="Comprar lasaña")
        Note.objects.create(user=self.other, title="Lasaña ajena")

        response = self.client.get(reverse("notes:search"), {"q": "lasaña"})
        self.assertContains(response, "Receta de lasaña")
        self.assertContains(response, "Comprar lasaña")
        self.assertNotContains(response, "Lasaña ajena")

    def test_sin_query_no_da_resultados(self):
        Note.objects.create(user=self.user, title="Algo")
        response = self.client.get(reverse("notes:search"))
        self.assertEqual(response.context["total"], 0)


class TaskReorderTests(TestCase):
    def setUp(self):
        self.user = make_user("notes14@test.local")
        self.other = make_user("notes15@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_reordenar_tareas_propias(self):
        a = Task.objects.create(user=self.user, title="A", order=0)
        b = Task.objects.create(user=self.user, title="B", order=1)

        response = self.client.post(
            reverse("notes:task-reorder"),
            data=json.dumps({"order": [b.pk, a.pk]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(b.order, 0)
        self.assertEqual(a.order, 1)

    def test_no_puede_reordenar_tareas_ajenas(self):
        ajena = Task.objects.create(user=self.other, title="Ajena", order=0)
        response = self.client.post(
            reverse("notes:task-reorder"),
            data=json.dumps({"order": [ajena.pk]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        ajena.refresh_from_db()
        self.assertEqual(ajena.order, 0)


class StatsTests(TestCase):
    def setUp(self):
        self.user = make_user("notes16@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_pagina_de_analiticas_carga(self):
        task = Task.objects.create(user=self.user, title="Hecha", priority=Priority.URGENT)
        task.mark_done()
        response = self.client.get(reverse("notes:stats"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["tasks_done_total"], 1)

    def test_racha_de_habito_en_analiticas(self):
        habit = Habit.objects.create(user=self.user, title="Meditar")
        habit.checkins.create(date=timezone.localdate())
        response = self.client.get(reverse("notes:stats"))
        self.assertEqual(response.context["best_streak"], 1)


class SubjectAndLectureNoteTests(TestCase):
    def setUp(self):
        self.user = make_user("notes17@test.local")
        self.other = make_user("notes18@test.local")
        self.client.login(username=self.user.username, password="Testpass123!")

    def test_crear_asignatura(self):
        response = self.client.post(reverse("notes:subject-list"), {
            "name": "Cálculo I", "color": "#7c6bf0", "icon": "📐",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subject.objects.filter(user=self.user, name="Cálculo I").exists())

    def test_anadir_apunte_a_una_asignatura(self):
        subject = Subject.objects.create(user=self.user, name="Historia")
        response = self.client.post(reverse("notes:subject-detail", args=[subject.pk]), {
            "date": timezone.localdate().isoformat(),
            "title": "Tema 1: La Revolución",
            "content": "Hoy se ha hablado de las causas económicas...",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(subject.lecture_notes.filter(title="Tema 1: La Revolución").exists())

    def test_no_se_ve_una_asignatura_ajena(self):
        subject = Subject.objects.create(user=self.other, name="Ajena")
        response = self.client.get(reverse("notes:subject-detail", args=[subject.pk]))
        self.assertEqual(response.status_code, 404)

    def test_cambiar_color_de_una_asignatura(self):
        subject = Subject.objects.create(user=self.user, name="Química", color="#7c6bf0")
        response = self.client.post(reverse("notes:subject-edit", args=[subject.pk]), {
            "name": "Química", "color": "#22c55e", "icon": subject.icon,
        })
        self.assertEqual(response.status_code, 302)
        subject.refresh_from_db()
        self.assertEqual(subject.color, "#22c55e")

    def test_no_se_puede_editar_asignatura_ajena(self):
        subject = Subject.objects.create(user=self.other, name="Ajena")
        response = self.client.get(reverse("notes:subject-edit", args=[subject.pk]))
        self.assertEqual(response.status_code, 404)

    def test_editar_apunte(self):
        subject = Subject.objects.create(user=self.user, name="Física")
        note = LectureNote.objects.create(subject=subject, title="Original", content="...")
        response = self.client.post(reverse("notes:lecture-note-edit", args=[note.pk]), {
            "date": timezone.localdate().isoformat(), "title": "Editado", "content": "Nuevo contenido",
        })
        self.assertEqual(response.status_code, 302)
        note.refresh_from_db()
        self.assertEqual(note.title, "Editado")

    def test_no_se_puede_editar_apunte_de_asignatura_ajena(self):
        subject = Subject.objects.create(user=self.other, name="Ajena")
        note = LectureNote.objects.create(subject=subject, title="Ajeno")
        response = self.client.get(reverse("notes:lecture-note-edit", args=[note.pk]))
        self.assertEqual(response.status_code, 404)

    def test_borrar_asignatura_borra_sus_apuntes(self):
        subject = Subject.objects.create(user=self.user, name="Química")
        LectureNote.objects.create(subject=subject, title="Apunte 1")
        self.client.post(reverse("notes:subject-delete", args=[subject.pk]))
        self.assertFalse(LectureNote.objects.filter(subject_id=subject.pk).exists())
