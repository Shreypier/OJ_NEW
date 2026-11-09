import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("home", "0005_problem_output_const")]
    operations = [
        migrations.CreateModel(
            name="TestCase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("input_data", models.TextField(blank=True)),
                ("expected_output", models.TextField(blank=True)),
                ("is_sample", models.BooleanField(default=False, help_text="Sample cases show input/expected/actual output to the user.")),
                ("order", models.PositiveIntegerField(default=0)),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="test_cases", to="home.problem")),
            ],
            options={"ordering": ["order", "id"]},
        ),
    ]
