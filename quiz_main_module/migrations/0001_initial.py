# Generated by Django 4.2.7 on 2023-12-02 20:56

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="User",
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
                ("username", models.CharField(max_length=50)),
                ("password", models.CharField(max_length=50)),
                (
                    "user_role",
                    models.CharField(
                        choices=[("user", "User"), ("admin", "Admin")], max_length=10
                    ),
                ),
                (
                    "user_type",
                    models.CharField(
                        choices=[("professor", "Professor"), ("student", "Student")],
                        max_length=20,
                    ),
                ),
                ("courses", models.JSONField(default=list)),
            ],
        ),
    ]
