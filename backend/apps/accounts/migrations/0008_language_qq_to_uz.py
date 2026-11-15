# Qoraqalpoq tili (qq) olib tashlandi: shu tildagi foydalanuvchilar uz ga o'tadi.

from django.db import migrations, models


def qq_to_uz(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(language="qq").update(language="uz")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_user_role_guest'),
    ]

    operations = [
        migrations.RunPython(qq_to_uz, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='language',
            field=models.CharField(choices=[('uz', "O'zbekcha (lotin)"), ('kr', 'Ўзбекча (кирилл)'), ('ru', 'Русский')], default='uz', max_length=3),
        ),
    ]
