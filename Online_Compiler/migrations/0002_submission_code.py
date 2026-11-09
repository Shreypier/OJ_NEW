from django.db import migrations


class Migration(migrations.Migration):
    # 0001_initial already creates the `code` column, so adding it again made a
    # fresh `migrate` fail with "duplicate column name". Kept as a no-op so the
    # migration history of existing databases stays valid.
    dependencies = [("Online_Compiler", "0001_initial")]
    operations = []
