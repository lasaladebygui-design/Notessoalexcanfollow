"""Cálculos del dashboard de Notas -- todo lo que no es un CRUD directo
vive aquí, igual que training/services.py en Tonnage."""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import Goal, Habit, Note, Priority, Task

PRIORITY_COLORS = {
    Priority.URGENT: "#ef4444",
    Priority.HIGH: "#f5b942",
    Priority.MEDIUM: "#b9bac4",
    Priority.LOW: "#7d7f8c",
}


def dashboard_summary(user):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    soon = today + timedelta(days=7)

    tasks = Task.objects.active().filter(user=user)
    pending = tasks.filter(is_done=False)

    habits = list(Habit.objects.active().filter(user=user, is_archived=False))
    habits_pending = [h for h in habits if not h.done_today()]

    return {
        "habits_pending": habits_pending,
        "habits_pending_count": len(habits_pending),
        "today": today,
        "pending_count": pending.count(),
        "completed_this_week": tasks.filter(is_done=True, completed_at__date__gte=week_start).count(),
        "overdue": pending.filter(due_date__lt=today).select_related("category").order_by("due_date")[:10],
        "overdue_count": pending.filter(due_date__lt=today).count(),
        "high_priority": pending.filter(priority__in=[Priority.HIGH, Priority.URGENT]).select_related("category").order_by("due_date")[:10],
        "high_priority_count": pending.filter(priority__in=[Priority.HIGH, Priority.URGENT]).count(),
        "due_today": pending.filter(due_date=today).select_related("category"),
        "upcoming": pending.filter(due_date__gt=today, due_date__lte=soon).select_related("category").order_by("due_date")[:10],
        "upcoming_reminders": Note.objects.active().filter(
            user=user, reminder_date__gte=today, reminder_date__lte=soon,
        ).order_by("reminder_date")[:10],
        "recent_notes": Note.objects.active().filter(user=user).select_related("category")[:6],
    }


def productivity_stats(user, weeks=8):
    """Todo lo que pinta la página de Analíticas. Las barras semanales se
    devuelven ya con el ancho en % calculado (respecto al máximo de la
    serie) para que la plantilla no tenga que hacer ninguna cuenta --
    así el pico de la serie siempre toca el 100% aunque cambie de semana
    a semana."""
    today = timezone.localdate()
    this_week_start = today - timedelta(days=today.weekday())

    weekly = []
    for i in range(weeks - 1, -1, -1):
        week_start = this_week_start - timedelta(weeks=i)
        week_end = week_start + timedelta(days=7)
        count = Task.objects.active().filter(
            user=user, is_done=True, completed_at__date__gte=week_start, completed_at__date__lt=week_end,
        ).count()
        weekly.append({"label": week_start.strftime("%d/%m"), "count": count})
    peak = max((w["count"] for w in weekly), default=0) or 1
    for w in weekly:
        w["pct"] = round(w["count"] / peak * 100)

    by_category = list(
        Task.objects.active().filter(user=user, category__isnull=False)
        .values("category__name", "category__color", "category__icon")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )
    cat_peak = max((c["total"] for c in by_category), default=0) or 1
    for c in by_category:
        c["pct"] = round(c["total"] / cat_peak * 100)

    priority_counts = dict(
        Task.objects.active().filter(user=user).values_list("priority").annotate(total=Count("id"))
    )
    by_priority = [
        {"key": key, "label": label, "count": priority_counts.get(key, 0), "color": PRIORITY_COLORS[key]}
        for key, label in Priority.choices
    ]
    priority_peak = max((p["count"] for p in by_priority), default=0) or 1
    for p in by_priority:
        p["pct"] = round(p["count"] / priority_peak * 100)

    habits = list(Habit.objects.active().filter(user=user, is_archived=False))
    habits_summary = sorted(
        [{"title": h.title, "streak": h.current_streak(), "done_today": h.done_today()} for h in habits],
        key=lambda h: -h["streak"],
    )

    goals = Goal.objects.active().filter(user=user)
    goals_achieved = goals.filter(is_achieved=True).count()
    goals_total = goals.count()

    month_start = today.replace(day=1)
    tasks_all = Task.objects.active().filter(user=user)

    return {
        "weekly": weekly,
        "by_category": by_category,
        "by_priority": by_priority,
        "habits_summary": habits_summary,
        "goals_achieved": goals_achieved,
        "goals_total": goals_total,
        "goals_pct": round(goals_achieved / goals_total * 100) if goals_total else 0,
        "tasks_total": tasks_all.count(),
        "tasks_done_total": tasks_all.filter(is_done=True).count(),
        "notes_this_month": Note.objects.active().filter(user=user, created_at__date__gte=month_start).count(),
        "best_streak": max((h["streak"] for h in habits_summary), default=0),
    }


def greeting(now=None):
    hour = (now or timezone.localtime()).hour
    if hour < 6:
        return "Buenas noches"
    if hour < 13:
        return "Buenos días"
    if hour < 20:
        return "Buenas tardes"
    return "Buenas noches"
