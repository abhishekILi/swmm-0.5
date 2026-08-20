from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("srar", "0002_alter_srarequipmentexploitation_sfd_details_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fullpowertrialsmainengine",
            name="conducted_by",
            field=models.IntegerField(
                blank=True,
                choices=[(1, "DTTT"), (2, "MTU"), (3, "CTT"), (4, "SS")],
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="fptdieselalternators",
            name="conducted_by",
            field=models.IntegerField(
                blank=True,
                choices=[(1, "DTT"), (2, "MTU"), (3, "CTT"), (4, "SS")],
                null=True,
            ),
        ),
    ]
