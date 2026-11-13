from django.db import migrations

COUNTRIES = [("KEN", "Kenya"), ("TZA", "Tanzania"), ("ETH", "Ethiopia")]


def seed_countries(apps, schema_editor):
    Country = apps.get_model("geography", "Country")
    for code, name in COUNTRIES:
        Country.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("geography", "0001_initial")]
    operations = [migrations.RunPython(seed_countries, migrations.RunPython.noop)]