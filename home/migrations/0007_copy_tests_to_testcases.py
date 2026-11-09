from django.db import migrations


def copy_tests(apps, schema_editor):
    Problem = apps.get_model("home", "problem")
    TestCase = apps.get_model("home", "TestCase")
    for p in Problem.objects.all():
        if (p.output_test or "").strip():
            TestCase.objects.create(problem=p, input_data=p.input_test or "",
                                    expected_output=p.output_test, is_sample=True, order=1)


def restore_tests(apps, schema_editor):
    Problem = apps.get_model("home", "problem")
    TestCase = apps.get_model("home", "TestCase")
    for p in Problem.objects.all():
        case = TestCase.objects.filter(problem=p).order_by("order", "id").first()
        if case:
            p.input_test, p.output_test = case.input_data, case.expected_output
            p.save()


class Migration(migrations.Migration):
    dependencies = [("home", "0006_testcase")]
    operations = [migrations.RunPython(copy_tests, restore_tests)]
