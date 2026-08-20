from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("srar", "0004_srar_new_table_display_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="equipment_type_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="equipment_desc",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="status",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="cmms_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="cmms_ship_id",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="equipment_category_code",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="universal_id_a_user_created_by",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="universal_id_a_user_updated_by",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="srarequipmenttypelist",
            name="universal_id_ch_master_equipment_type",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
