import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("home", "0008_remove_problem_tests"),
        ("Online_Compiler", "0006_submission"),
    ]
    operations = [
        migrations.DeleteModel(name="submission"),
        migrations.DeleteModel(name="User_Input"),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(max_length=50)),
                ("code", models.TextField(blank=True)),
                ("verdict", models.CharField(max_length=10)),
                ("message", models.TextField(blank=True)),
                ("time_ms", models.PositiveIntegerField(default=0)),
                ("passed", models.PositiveIntegerField(default=0)),
                ("total", models.PositiveIntegerField(default=0)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to="home.problem")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="submissions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created", "-id"]},
        ),
    ]
