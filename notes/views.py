import calendar as calendar_module
import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.google_calendar import google_calendar_enabled

from .calendar_sync import delete_event_for, sync_event
from .forms import (
    CategoryForm, GoalForm, GoalStepForm, HabitForm, LectureNoteForm, NoteForm, SubjectForm, TagForm, TaskForm,
)
from .models import Category, Goal, GoalStep, Habit, LectureNote, Note, Priority, Subject, Tag, Task
from .services import dashboard_summary, greeting, productivity_stats

MONTH_NAMES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# --- Dashboard -----------------------------------------------------------

@login_required
def dashboard(request):
    summary = dashboard_summary(request.user)
    return render(request, "notes/dashboard.html", {**summary, "greeting": greeting()})


@login_required
def stats(request):
    return render(request, "notes/stats.html", productivity_stats(request.user))


# --- Búsqueda global -------------------------------------------------------

@login_required
def global_search(request):
    query = request.GET.get("q", "").strip()
    results = {"notes": [], "tasks": [], "habits": [], "goals": [], "lecture_notes": []}
    if query:
        results["notes"] = Note.objects.filter(user=request.user).filter(
            Q(title__icontains=query) | Q(body__icontains=query)
        ).select_related("category")[:8]
        results["tasks"] = Task.objects.filter(user=request.user).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).select_related("category")[:8]
        results["habits"] = Habit.objects.filter(user=request.user, title__icontains=query)[:8]
        results["goals"] = Goal.objects.filter(user=request.user).filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:8]
        results["lecture_notes"] = LectureNote.objects.filter(subject__user=request.user).filter(
            Q(title__icontains=query) | Q(content__icontains=query) | Q(subject__name__icontains=query)
        ).select_related("subject")[:8]
    total = sum(len(v) for v in results.values())
    return render(request, "notes/search.html", {"query": query, "results": results, "total": total})


# --- Notas -----------------------------------------------------------------

@login_required
def note_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    tag_id = request.GET.get("tag", "")

    notes = Note.objects.filter(user=request.user).select_related("category").prefetch_related("tags")
    if query:
        notes = notes.filter(Q(title__icontains=query) | Q(body__icontains=query))
    if category_id:
        notes = notes.filter(category_id=category_id)
    if tag_id:
        notes = notes.filter(tags__id=tag_id)

    return render(request, "notes/note_list.html", {
        "notes": notes.distinct(), "query": query, "category_id": category_id, "tag_id": tag_id,
        "categories": Category.objects.filter(user=request.user),
        "tags": Tag.objects.filter(user=request.user),
    })


@login_required
def note_create(request):
    if request.method == "POST":
        form = NoteForm(request.POST, user=request.user)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            form.save_m2m()
            sync_event(request.user, note, "reminder_date", old_date=None)
            messages.success(request, "Nota creada.")
            return redirect("notes:note-list")
    else:
        form = NoteForm(user=request.user)
    return render(request, "notes/note_form.html", {"form": form, "is_new": True})


@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    if request.method == "POST":
        old_date = note.reminder_date
        form = NoteForm(request.POST, instance=note, user=request.user)
        if form.is_valid():
            note = form.save()
            sync_event(request.user, note, "reminder_date", old_date=old_date)
            messages.success(request, "Nota actualizada.")
            return redirect("notes:note-list")
    else:
        form = NoteForm(instance=note, user=request.user)
    return render(request, "notes/note_form.html", {"form": form, "note": note, "is_new": False})


@login_required
@require_POST
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    delete_event_for(request.user, note)
    note.delete()
    return redirect("notes:note-list")


@login_required
@require_POST
def note_toggle_pin(request, pk):
    note = get_object_or_404(Note, pk=pk, user=request.user)
    note.is_pinned = not note.is_pinned
    note.save(update_fields=["is_pinned"])
    return redirect(request.META.get("HTTP_REFERER") or "notes:note-list")


# --- Tareas ------------------------------------------------------------

@login_required
def task_list(request):
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    priority = request.GET.get("priority", "")
    show = request.GET.get("show", "pending")

    tasks = Task.objects.filter(user=request.user, parent__isnull=True).select_related("category").prefetch_related("tags", "subtasks")
    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category_id:
        tasks = tasks.filter(category_id=category_id)
    if priority:
        tasks = tasks.filter(priority=priority)
    if show == "pending":
        tasks = tasks.filter(is_done=False)
    elif show == "done":
        tasks = tasks.filter(is_done=True)

    return render(request, "notes/task_list.html", {
        "tasks": tasks.distinct(), "query": query, "category_id": category_id, "priority": priority, "show": show,
        "categories": Category.objects.filter(user=request.user),
        "priorities": Priority.choices,
    })


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            form.save_m2m()
            sync_event(request.user, task, "due_date", old_date=None)
            messages.success(request, "Tarea creada.")
            return redirect("notes:task-list")
    else:
        initial = {}
        parent_id = request.GET.get("parent")
        if parent_id:
            initial["parent"] = parent_id
        form = TaskForm(user=request.user, initial=initial)
    return render(request, "notes/task_form.html", {"form": form, "is_new": True})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    if request.method == "POST":
        old_date = task.due_date
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            task = form.save()
            sync_event(request.user, task, "due_date", old_date=old_date)
            messages.success(request, "Tarea actualizada.")
            return redirect("notes:task-list")
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, "notes/task_form.html", {"form": form, "task": task, "is_new": False})


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    delete_event_for(request.user, task)
    task.delete()
    return redirect("notes:task-list")


@login_required
@require_POST
def task_toggle_done(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user)
    task.mark_done(not task.is_done)
    return redirect(request.META.get("HTTP_REFERER") or "notes:task-list")


@login_required
@require_POST
def task_reorder(request):
    try:
        ordered_ids = json.loads(request.body)["order"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return HttpResponseBadRequest("order inválido")

    own_ids = set(Task.objects.filter(user=request.user, pk__in=ordered_ids).values_list("pk", flat=True))
    tasks = []
    for position, task_id in enumerate(ordered_ids):
        if task_id in own_ids:
            tasks.append(Task(pk=task_id, order=position))
    Task.objects.bulk_update(tasks, ["order"])
    return JsonResponse({"ok": True})


# --- Categorías y etiquetas ---------------------------------------------

@login_required
def category_list(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, f"Categoría «{category.name}» creada.")
            return redirect("notes:category-list")
    else:
        form = CategoryForm()

    tag_form = TagForm()
    return render(request, "notes/category_list.html", {
        "categories": Category.objects.filter(user=request.user),
        "tags": Tag.objects.filter(user=request.user),
        "form": form, "tag_form": tag_form,
    })


@login_required
@require_POST
def category_delete(request, pk):
    get_object_or_404(Category, pk=pk, user=request.user).delete()
    return redirect("notes:category-list")


@login_required
@require_POST
def tag_create(request):
    form = TagForm(request.POST)
    if form.is_valid():
        Tag.objects.get_or_create(user=request.user, name=form.cleaned_data["name"])
    return redirect("notes:category-list")


@login_required
@require_POST
def tag_delete(request, pk):
    get_object_or_404(Tag, pk=pk, user=request.user).delete()
    return redirect("notes:category-list")


# --- Hábitos -------------------------------------------------------------

@login_required
def habit_list(request):
    if request.method == "POST":
        form = HabitForm(request.POST, user=request.user)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, f"Hábito «{habit.title}» creado.")
            return redirect("notes:habit-list")
    else:
        form = HabitForm(user=request.user)

    return render(request, "notes/habit_list.html", {
        "habits": Habit.objects.filter(user=request.user, is_archived=False).select_related("category"),
        "form": form,
    })


@login_required
@require_POST
def habit_toggle_checkin(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    today = timezone.localdate()
    checkin, created = habit.checkins.get_or_create(date=today)
    if not created:
        checkin.delete()
    return redirect(request.META.get("HTTP_REFERER") or "notes:habit-list")


@login_required
@require_POST
def habit_delete(request, pk):
    get_object_or_404(Habit, pk=pk, user=request.user).delete()
    return redirect("notes:habit-list")


# --- Objetivos -------------------------------------------------------------

@login_required
def goal_list(request):
    return render(request, "notes/goal_list.html", {
        "goals": Goal.objects.filter(user=request.user).prefetch_related("steps"),
    })


@login_required
def goal_create(request):
    if request.method == "POST":
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, "Objetivo creado.")
            return redirect("notes:goal-detail", pk=goal.pk)
    else:
        form = GoalForm()
    return render(request, "notes/goal_form.html", {"form": form, "is_new": True})


@login_required
def goal_detail(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == "POST":
        step_form = GoalStepForm(request.POST)
        if step_form.is_valid():
            step = step_form.save(commit=False)
            step.goal = goal
            step.order = goal.steps.count()
            step.save()
            return redirect("notes:goal-detail", pk=goal.pk)
    else:
        step_form = GoalStepForm()
    return render(request, "notes/goal_detail.html", {
        "goal": goal, "step_form": step_form,
    })


@login_required
def goal_edit(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, "Objetivo actualizado.")
            return redirect("notes:goal-detail", pk=goal.pk)
    else:
        form = GoalForm(instance=goal)
    return render(request, "notes/goal_form.html", {"form": form, "goal": goal, "is_new": False})


@login_required
@require_POST
def goal_delete(request, pk):
    get_object_or_404(Goal, pk=pk, user=request.user).delete()
    return redirect("notes:goal-list")


@login_required
@require_POST
def goal_toggle_achieved(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    goal.mark_achieved(not goal.is_achieved)
    return redirect("notes:goal-detail", pk=goal.pk)


@login_required
@require_POST
def goal_step_toggle(request, pk):
    step = get_object_or_404(GoalStep, pk=pk, goal__user=request.user)
    step.is_done = not step.is_done
    step.save(update_fields=["is_done"])
    return redirect("notes:goal-detail", pk=step.goal_id)


@login_required
@require_POST
def goal_step_delete(request, pk):
    step = get_object_or_404(GoalStep, pk=pk, goal__user=request.user)
    goal_id = step.goal_id
    step.delete()
    return redirect("notes:goal-detail", pk=goal_id)


# --- Apuntes de la uni ----------------------------------------------------

@login_required
def subject_list(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.user = request.user
            subject.save()
            messages.success(request, f"Asignatura «{subject.name}» creada.")
            return redirect("notes:subject-list")
    else:
        form = SubjectForm()

    subjects = Subject.objects.filter(user=request.user).annotate(notes_count=Count("lecture_notes"))
    return render(request, "notes/subject_list.html", {"subjects": subjects, "form": form})


@login_required
@require_POST
def subject_delete(request, pk):
    get_object_or_404(Subject, pk=pk, user=request.user).delete()
    return redirect("notes:subject-list")


@login_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            messages.success(request, "Asignatura actualizada.")
            return redirect("notes:subject-detail", pk=subject.pk)
    else:
        form = SubjectForm(instance=subject)
    return render(request, "notes/subject_form.html", {"form": form, "subject": subject})


@login_required
def subject_detail(request, pk):
    subject = get_object_or_404(Subject, pk=pk, user=request.user)
    if request.method == "POST":
        form = LectureNoteForm(request.POST, request.FILES)
        if form.is_valid():
            lecture_note = form.save(commit=False)
            lecture_note.subject = subject
            lecture_note.save()
            messages.success(request, "Apunte guardado.")
            return redirect("notes:subject-detail", pk=subject.pk)
    else:
        form = LectureNoteForm(initial={"date": timezone.localdate()})

    return render(request, "notes/subject_detail.html", {
        "subject": subject,
        "lecture_notes": subject.lecture_notes.all(),
        "form": form,
    })


@login_required
def lecture_note_edit(request, pk):
    lecture_note = get_object_or_404(LectureNote, pk=pk, subject__user=request.user)
    if request.method == "POST":
        form = LectureNoteForm(request.POST, request.FILES, instance=lecture_note)
        if form.is_valid():
            form.save()
            messages.success(request, "Apunte actualizado.")
            return redirect("notes:subject-detail", pk=lecture_note.subject_id)
    else:
        form = LectureNoteForm(instance=lecture_note)
    return render(request, "notes/lecture_note_form.html", {"form": form, "lecture_note": lecture_note})


@login_required
@require_POST
def lecture_note_delete(request, pk):
    lecture_note = get_object_or_404(LectureNote, pk=pk, subject__user=request.user)
    subject_id = lecture_note.subject_id
    lecture_note.delete()
    return redirect("notes:subject-detail", pk=subject_id)


# --- Calendario ----------------------------------------------------------

def _parse_calendar_month(request, today):
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        first_of_month = date(year, month, 1)
    except (TypeError, ValueError):
        raise Http404
    return year, month, first_of_month


@login_required
def calendar_view(request):
    today = timezone.localdate()
    year, month, first_of_month = _parse_calendar_month(request, today)

    raw_weeks = calendar_module.Calendar(firstweekday=0).monthdatescalendar(year, month)

    tasks = Task.objects.filter(user=request.user, due_date__year=year, due_date__month=month)
    notes = Note.objects.filter(user=request.user, reminder_date__year=year, reminder_date__month=month)
    items_by_date = {}
    for task in tasks:
        items_by_date.setdefault(task.due_date, []).append({"kind": "task", "obj": task})
    for note in notes:
        items_by_date.setdefault(note.reminder_date, []).append({"kind": "note", "obj": note})

    weeks = [
        [
            {"date": day, "in_month": day.month == month, "is_today": day == today, "items": items_by_date.get(day, [])}
            for day in week
        ]
        for week in raw_weeks
    ]

    prev_month_date = first_of_month - timedelta(days=1)
    next_month_date = (first_of_month + timedelta(days=32)).replace(day=1)

    return render(request, "notes/calendar.html", {
        "weeks": weeks, "year": year, "month": month,
        "month_label": f"{MONTH_NAMES_ES[month]} {year}",
        "prev_year": prev_month_date.year, "prev_month": prev_month_date.month,
        "next_year": next_month_date.year, "next_month": next_month_date.month,
        "google_calendar_enabled": google_calendar_enabled(),
        "google_calendar_connected": hasattr(request.user, "google_calendar_connection"),
    })
