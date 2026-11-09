from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def _is_hashed(value):
    try:
        identify_hasher(value)
        return True
    except ValueError:
        return False


def employees_to_staff(apps, schema_editor):
    """Turn legacy user_employee rows into real staff users (passwords hashed)."""
    Legacy = apps.get_model("accounts", "user_employee")
    User = apps.get_model("auth", "User")
    for emp in Legacy.objects.all():
        user, _ = User.objects.get_or_create(username=emp.employee_id)
        user.is_staff = True
        user.password = emp.password if _is_hashed(emp.password) else make_password(emp.password)
        user.save()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_alter_user_employee_employee_id"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(employees_to_staff, migrations.RunPython.noop)]
