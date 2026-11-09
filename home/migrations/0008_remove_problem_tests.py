from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("home", "0007_copy_tests_to_testcases")]
    operations = [
        migrations.RemoveField(model_name="problem", name="input_test"),
        migrations.RemoveField(model_name="problem", name="output_test"),
    ]
