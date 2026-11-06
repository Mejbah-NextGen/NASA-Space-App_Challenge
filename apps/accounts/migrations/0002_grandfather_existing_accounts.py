from django.db import migrations


def grandfather_existing_accounts(apps, schema_editor):
    user_model = apps.get_model("accounts", "User")
    user_model.objects.filter(is_verified=False).update(is_verified=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(grandfather_existing_accounts, migrations.RunPython.noop),
    ]
