from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_employees_to_staff_users")]
    operations = [
        migrations.DeleteModel(name="employee"),
        migrations.DeleteModel(name="user_employee"),
    ]
