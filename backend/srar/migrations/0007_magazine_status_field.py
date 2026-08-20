from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("srar", "0006_srar_master_equipment"),
    ]

    operations = [
        migrations.AddField(
            "magazineffsystemfloodingsystem",
            "status",
            models.IntegerField(
                choices=[(1, "SAT"), (2, "Unsat")], null=True, blank=True
            ),
        ),
    ]
