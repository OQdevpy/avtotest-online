"""Har savol faqat bitta biletda (variantda) — bazadagi cheklov."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0012_question_published"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="ticketquestion",
            constraint=models.UniqueConstraint(
                fields=("question",), name="ticketquestion_one_ticket"
            ),
        ),
    ]
