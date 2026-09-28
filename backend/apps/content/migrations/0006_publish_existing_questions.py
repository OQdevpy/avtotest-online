"""Mavjud savollarni nashr etilgan deb belgilaydi.

`is_published` yangi maydon, default False. Importdan kelgan 1152 savol
allaqachon jonli edi, shuning uchun ular True bo'lishi kerak — aks holda
migratsiyadan keyin o'quvchida savol qolmaydi.
"""

from django.db import migrations


def publish_existing(apps, schema_editor):
    apps.get_model("content", "Question").objects.update(is_published=True)


def unpublish_all(apps, schema_editor):
    apps.get_model("content", "Question").objects.update(is_published=False)


class Migration(migrations.Migration):
    dependencies = [("content", "0005_question_is_in_web_question_is_published")]

    operations = [migrations.RunPython(publish_existing, unpublish_all)]
