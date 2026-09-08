import uuid

from django.db import migrations, models


def assign_unique_tokens(apps, schema_editor):
    Subject = apps.get_model("notes", "Subject")
    for subject in Subject.objects.all():
        subject.share_token = uuid.uuid4()
        subject.save(update_fields=["share_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("notes", "0004_lecturenote_pdf"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="is_shared",
            field=models.BooleanField(default=False, verbose_name="compartida"),
        ),
        migrations.AddField(
            model_name="subject",
            name="share_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, verbose_name="token para compartir"),
        ),
        migrations.RunPython(assign_unique_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="subject",
            name="share_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="token para compartir"),
        ),
    ]
