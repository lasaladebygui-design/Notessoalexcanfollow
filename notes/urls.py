from django.urls import path

from . import views

app_name = "notes"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("analiticas/", views.stats, name="stats"),
    path("estas-sin-conexion/", views.offline, name="offline"),
    path("sw.js", views.service_worker, name="service-worker"),
    path("buscar/", views.global_search, name="search"),

    path("notas/", views.note_list, name="note-list"),
    path("notas/nueva/", views.note_create, name="note-create"),
    path("notas/<int:pk>/editar/", views.note_edit, name="note-edit"),
    path("notas/<int:pk>/borrar/", views.note_delete, name="note-delete"),
    path("notas/<int:pk>/fijar/", views.note_toggle_pin, name="note-toggle-pin"),

    path("tareas/", views.task_list, name="task-list"),
    path("tareas/nueva/", views.task_create, name="task-create"),
    path("tareas/<int:pk>/editar/", views.task_edit, name="task-edit"),
    path("tareas/<int:pk>/borrar/", views.task_delete, name="task-delete"),
    path("tareas/<int:pk>/hecha/", views.task_toggle_done, name="task-toggle-done"),
    path("tareas/reordenar/", views.task_reorder, name="task-reorder"),

    path("organizar/", views.category_list, name="category-list"),
    path("organizar/categoria/<int:pk>/borrar/", views.category_delete, name="category-delete"),
    path("organizar/etiqueta/nueva/", views.tag_create, name="tag-create"),
    path("organizar/etiqueta/<int:pk>/borrar/", views.tag_delete, name="tag-delete"),

    path("habitos/", views.habit_list, name="habit-list"),
    path("habitos/<int:pk>/marcar/", views.habit_toggle_checkin, name="habit-toggle-checkin"),
    path("habitos/<int:pk>/borrar/", views.habit_delete, name="habit-delete"),

    path("objetivos/", views.goal_list, name="goal-list"),
    path("objetivos/nuevo/", views.goal_create, name="goal-create"),
    path("objetivos/<int:pk>/", views.goal_detail, name="goal-detail"),
    path("objetivos/<int:pk>/editar/", views.goal_edit, name="goal-edit"),
    path("objetivos/<int:pk>/borrar/", views.goal_delete, name="goal-delete"),
    path("objetivos/<int:pk>/conseguido/", views.goal_toggle_achieved, name="goal-toggle-achieved"),
    path("objetivos/paso/<int:pk>/marcar/", views.goal_step_toggle, name="goal-step-toggle"),
    path("objetivos/paso/<int:pk>/borrar/", views.goal_step_delete, name="goal-step-delete"),

    path("uni/", views.subject_list, name="subject-list"),
    path("uni/<int:pk>/", views.subject_detail, name="subject-detail"),
    path("uni/<int:pk>/editar/", views.subject_edit, name="subject-edit"),
    path("uni/<int:pk>/borrar/", views.subject_delete, name="subject-delete"),
    path("uni/<int:pk>/compartir/", views.subject_toggle_share, name="subject-toggle-share"),
    path("uni/apunte/<int:pk>/editar/", views.lecture_note_edit, name="lecture-note-edit"),
    path("uni/apunte/<int:pk>/borrar/", views.lecture_note_delete, name="lecture-note-delete"),
    path("uni/apunte/<int:pk>/pdf/", views.lecture_note_pdf, name="lecture-note-pdf"),
    path("compartido/<uuid:token>/", views.shared_subject, name="shared-subject"),

    path("eventos/nuevo/", views.event_create, name="event-create"),
    path("eventos/<int:pk>/editar/", views.event_edit, name="event-edit"),
    path("eventos/<int:pk>/borrar/", views.event_delete, name="event-delete"),

    path("calendario/", views.calendar_view, name="calendar"),

    path("eliminados/", views.trash, name="trash"),
    path("eliminados/<str:kind>/<int:pk>/restaurar/", views.trash_restore, name="trash-restore"),
    path("eliminados/<str:kind>/<int:pk>/borrar-para-siempre/", views.trash_delete_forever, name="trash-delete-forever"),
    path("eliminados/vaciar/", views.trash_empty, name="trash-empty"),
]
