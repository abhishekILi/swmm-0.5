from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("master", "0005_subdepartment_active_subdepartment_code_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="supplier",
            name="city",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="country",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="master.country",
            ),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="supplier_manufacture",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="contact_person",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="contact_number",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="supplier",
            name="email_id",
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name="mequipment",
            name="model",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
