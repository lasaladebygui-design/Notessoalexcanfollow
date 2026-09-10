from django.contrib import admin

from .models import Category, Event, LectureNote, Note, Subject, Tag, Task


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "icon", "color")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "is_pinned", "reminder_date", "updated_at")
    list_filter = ("user", "category", "is_pinned")
    search_fields = ("title", "body")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "priority", "due_date", "is_done", "parent")
    list_filter = ("user", "category", "priority", "is_done")
    search_fields = ("title", "description")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "icon", "color")
    list_filter = ("user",)
    search_fields = ("name",)


@admin.register(LectureNote)
class LectureNoteAdmin(admin.ModelAdmin):
    list_display = ("__str__", "subject", "date")
    list_filter = ("subject",)
    search_fields = ("title", "content")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "date", "start_time", "end_time", "category")
    list_filter = ("user", "category")
    search_fields = ("title", "description")
