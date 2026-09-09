from django import forms

from .models import Category, Goal, GoalStep, Habit, LectureNote, Note, Subject, Tag, Task


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["title", "body", "category", "tags", "reminder_date", "is_pinned"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
            "reminder_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "Sin categoría"
        self.fields["tags"].queryset = user.note_tags.all() if user else self.fields["tags"].queryset.none()


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "category", "tags", "priority", "due_date", "parent"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "due_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "tags": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "Sin categoría"
        self.fields["tags"].queryset = user.note_tags.all() if user else self.fields["tags"].queryset.none()
        self.fields["parent"].queryset = Task.objects.filter(user=user, parent__isnull=True)
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "Ninguna (tarea principal)"


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "color", "icon"]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]


class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = ["title", "category"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["category"].required = False
        self.fields["category"].empty_label = "Sin categoría"


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ["title", "description", "category", "target_date"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "target_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }


class GoalStepForm(forms.ModelForm):
    class Meta:
        model = GoalStep
        fields = ["title"]


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "color", "icon"]
        widgets = {
            "color": forms.TextInput(attrs={"type": "color"}),
        }


class LectureNoteForm(forms.ModelForm):
    # No es un campo del modelo (pdf_data es un BinaryField, no un FileField)
    # -- la vista lee este campo y vuelca los bytes a pdf_data/pdf_filename
    # a mano. Así el archivo se guarda en la propia base de datos en vez de
    # en el disco de Render (ver comentario en el modelo).
    pdf = forms.FileField(
        label="PDF", required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "application/pdf"}),
        help_text="Diapositivas o material de la clase, opcional.",
    )

    class Meta:
        model = LectureNote
        fields = ["date", "title", "content"]
        widgets = {
            "date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "title": forms.TextInput(attrs={"placeholder": "Título del tema (opcional)"}),
            "content": forms.Textarea(attrs={"rows": 10, "placeholder": "Escribe aquí todo lo que se ha dicho en clase..."}),
        }

    def clean_pdf(self):
        pdf = self.cleaned_data.get("pdf")
        if pdf and not pdf.name.lower().endswith(".pdf"):
            raise forms.ValidationError("El archivo debe ser un PDF.")
        return pdf

    def save(self, commit=True):
        instance = super().save(commit=False)
        pdf = self.cleaned_data.get("pdf")
        if pdf:
            instance.pdf_data = pdf.read()
            instance.pdf_filename = pdf.name
        if commit:
            instance.save()
        return instance
