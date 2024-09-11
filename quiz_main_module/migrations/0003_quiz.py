# Generated by Django 4.2.7 on 2023-12-03 05:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quiz_generator", "0002_questions"),
    ]

    operations = [
        migrations.CreateModel(
            name="Quiz",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("course", models.CharField(max_length=255)),
                ("num_questions", models.IntegerField()),
                ("quiz_duration", models.IntegerField()),
                ("quiz_expire_date", models.DateField()),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="quiz_generator.user",
                    ),
                ),
            ],
        ),
    ]
