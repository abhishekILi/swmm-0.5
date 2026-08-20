import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("srar", "0007_magazine_status_field"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="safetydevicechecktrial",
            name="sdc_conducted_by",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="fullpowertrialsmainengine",
            name="conducted_by",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="fptdieselalternators",
            name="conducted_by",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.CreateModel(
            name="ChMasterFullPowerConductedBy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now=True, null=True)),
                ("created_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("modified_on", models.DateTimeField(auto_now=True, null=True)),
                ("modified_ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "active",
                    models.SmallIntegerField(
                        choices=[(1, "active"), (2, "Inactive"), (3, "Delete")],
                        default=1,
                    ),
                ),
                (
                    "full_power_conducted_by_id",
                    models.CharField(max_length=250, unique=True),
                ),
                (
                    "full_power_conducted_by",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                ("cmms_status", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "universal_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_created_user",
                        to="users.customuserprofile",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_modified_user",
                        to="users.customuserprofile",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
        migrations.CreateModel(
            name="CmmsLubricant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_on", models.DateTimeField(auto_now=True, null=True)),
                ("created_ip", models.GenericIPAddressField(blank=True, null=True)),
                ("modified_on", models.DateTimeField(auto_now=True, null=True)),
                ("modified_ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "active",
                    models.SmallIntegerField(
                        choices=[(1, "active"), (2, "Inactive"), (3, "Delete")],
                        default=1,
                    ),
                ),
                ("lubricant_id", models.CharField(max_length=250, unique=True)),
                (
                    "lubricant_name",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                (
                    "lubricant_type",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "lubricant_code",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                ("unit", models.CharField(blank=True, max_length=50, null=True)),
                ("cmms_active", models.BooleanField(default=True)),
                (
                    "universal_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_created_user",
                        to="users.customuserprofile",
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_modified_user",
                        to="users.customuserprofile",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
