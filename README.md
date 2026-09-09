# Notas

Aplicación web de organización personal hecha con Django: notas, tareas, hábitos, objetivos, apuntes de la uni, calendario y analíticas, todo en un mismo sitio.

## Funcionalidades

- **Notas** — con categorías, etiquetas y fecha de recordatorio (sincronizable con Google Calendar).
- **Tareas** — subtareas, prioridad, categorías, etiquetas, fecha límite, reordenación por arrastrar y soltar.
- **Hábitos** — marca diaria con cálculo de racha.
- **Objetivos** — divididos en pasos, con barra de progreso derivada automáticamente.
- **Uni** — apuntes de clase organizados por asignatura, con PDF adjunto y enlace público para compartir con amigos (sin necesidad de cuenta).
- **Calendario** — vista mensual con tareas y notas.
- **Analíticas** — tareas completadas por semana, por categoría y por prioridad, rachas de hábitos, progreso de objetivos.
- **Búsqueda global** — en notas, tareas, hábitos, objetivos y apuntes a la vez.

## Stack

Django, PostgreSQL (Supabase) en producción / SQLite en local, Tailwind (CDN) + Alpine.js, Whitenoise para estáticos, despliegue en Render.

## Desarrollo local

```bash
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
copy .env.example .env      # rellena lo que necesites; vacío = SQLite local
python manage.py migrate
python manage.py runserver
```

## Variables de entorno

Ver `.env.example` para la lista completa (base de datos, Google Calendar OAuth opcional, etc).
