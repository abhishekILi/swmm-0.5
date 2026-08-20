# Generated migration for new SFD architectural fields and addon models in 0006

import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sfd", "0005_add_new_sfd_addon_fields_and_tables"),
        ("users", "0001_initial"),
        ("ilms", "0001_initial"),
        ("master", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompartmentMaster",
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
                ("name", models.CharField(max_length=250)),
                ("main_deck", models.BooleanField(blank=True, null=True)),
                (
                    "upper_deck",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("01", "01"),
                            ("02", "02"),
                            ("03", "03"),
                            ("04", "04"),
                            ("05", "05"),
                            ("06", "06"),
                            ("07", "07"),
                            ("08", "08"),
                            ("09", "09"),
                            ("10", "10"),
                        ],
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "lower_deck",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("1", "1"),
                            ("2", "2"),
                            ("3", "3"),
                            ("4", "4"),
                            ("5", "5"),
                            ("6", "6"),
                            ("7", "7"),
                            ("8", "8"),
                            ("9", "9"),
                            ("10", "10"),
                        ],
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "frame_station_from",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "frame_station_to",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Port, Aft", "Port, Aft"),
                            ("Port, Forward", "Port, Forward"),
                            ("Starboard, Forward", "Starboard, Forward"),
                            ("Starboard, Aft", "Starboard, Aft"),
                        ],
                        max_length=30,
                        null=True,
                    ),
                ),
                ("is_deleted", models.BooleanField(default=False)),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, null=True),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, null=True)),
            ],
            options={
                "verbose_name": "Compartment",
                "verbose_name_plural": "Compartments",
            },
        ),
        migrations.CreateModel(
            name="ReportExportJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("report_key", models.CharField(max_length=100)),
                (
                    "export_format",
                    models.CharField(
                        choices=[("excel", "Excel"), ("pdf", "PDF")],
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("success", "Success"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                (
                    "file_path",
                    models.CharField(blank=True, max_length=500, null=True),
                ),
                ("error", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "sfd_reportexportjob",
            },
        ),
        migrations.CreateModel(
            name="EquipmentCompartmentMapping",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, null=True),
                ),
                (
                    "compartment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="equipment_mappings",
                        to="sfd.compartmentmaster",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sfd_equipment_compartment_mappings",
                        to="users.customuserprofile",
                    ),
                ),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="compartment_mappings",
                        to="sfd.equipment",
                    ),
                ),
            ],
            options={
                "unique_together": {("equipment", "compartment")},
            },
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="ship_type",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="equipment_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_equipment_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_system_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="equipment_model",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="equipment_code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="ilms_eq_code",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="equipment_direction",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="equipment_section",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_installation_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="authority_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_service_life",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="authority_of_removal",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="authority_of_installation",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="removal_remark",
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="type",
            field=models.CharField(
                blank=True,
                choices=[("equipment", "Equipment"), ("system", "System")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("cat1", "Cat 1"),
                    ("cat2", "Cat 2"),
                    ("cat3", "Cat 3"),
                    ("survey", "Survey & Demand"),
                    ("local_purchase", "Local Purchase"),
                ],
                max_length=30,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="mapping_status",
            field=models.CharField(
                blank=True,
                choices=[("mapped", "Mapped"), ("unmapped", "Unmapped")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="mapped_to",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="mapped_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="is_system",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="maintop_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_supplier_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_manufacturer_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_nomenclature",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_equipment_sr_no",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="new_oem_part_no",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_ship",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_equipment",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_srar_type",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_supplier",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_manufacturer",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_equipment_parent",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_department",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_t_maintop_header",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_ch_master_equipment_type",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_m_sub_department",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="rshi",
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name="RH at Installation",
            ),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_t_ship_detail",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="universal_id_t_equipment_ship_detail",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sfd_ship_equipment_created",
                to="users.customuserprofile",
            ),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="system",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ship_systems_sfd",
                to="sfd.equipment",
            ),
        ),
        migrations.AddField(
            model_name="shipequipment",
            name="manufacturer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="manufactured_equipments_sfd",
                to="sfd.supplier",
            ),
        ),
    ]
