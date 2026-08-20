from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("srar", "0005_srar_equipment_type_list_cmms_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="SrarMasterEquipment",
            fields=[
                (
                    "equipment_type_id",
                    models.CharField(
                        db_column="Equipment_Type_ID",
                        max_length=255,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "equipment_desc",
                    models.CharField(
                        blank=True,
                        db_column="Equipment_Desc",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True, db_column="Status", max_length=50, null=True
                    ),
                ),
                (
                    "cmms_id",
                    models.CharField(
                        blank=True, db_column="CMMS_ID", max_length=100, null=True
                    ),
                ),
                (
                    "cmms_ship_id",
                    models.CharField(
                        blank=True,
                        db_column="CMMS_Ship_ID",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "equipment_category_code",
                    models.CharField(
                        blank=True,
                        db_column="Equipment_Category_Code",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "universal_id_a_user_created_by",
                    models.CharField(
                        blank=True,
                        db_column="Universal_ID_A_User_Created_By",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "universal_id_a_user_updated_by",
                    models.CharField(
                        blank=True,
                        db_column="Universal_ID_A_User_Updated_By",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "created_date",
                    models.DateTimeField(
                        blank=True, db_column="CreatedDate", null=True
                    ),
                ),
                (
                    "updated_date",
                    models.DateTimeField(
                        blank=True, db_column="UpdatedDate", null=True
                    ),
                ),
                (
                    "universal_id_ch_master_equipment_type",
                    models.CharField(
                        blank=True,
                        db_column="Universal_ID_Ch_Master_Equipment_Type",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "order_by",
                    models.IntegerField(blank=True, db_column="Order_By", null=True),
                ),
            ],
            options={
                "db_table": "srar_masterequipment",
                "ordering": ["order_by", "equipment_type_id"],
            },
        ),
    ]
