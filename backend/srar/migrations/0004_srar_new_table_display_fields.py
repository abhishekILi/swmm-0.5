from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("srar", "0003_alter_fpt_main_engine_conducted_by_choices"),
    ]

    operations = [
        migrations.AddField(
            "reductiongearexploitation",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitation",
            "nomenclature",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitation",
            "eqpt_code",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitation",
            "loc_on_board",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbineexploitation",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbineexploitation",
            "nomenclature",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbineexploitation",
            "eqpt_code",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbineexploitation",
            "loc_on_board",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "replacementofmajorassemblies",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "replacementofmajorassemblies",
            "eqpt_sr_number",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "annualsrmrroutineundertaken",
            "undertaken_by_whom",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbinegeneratorexploitation",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbinegeneratorexploitation",
            "nomenclature",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbinegeneratorexploitation",
            "eqpt_code",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "gasturbinegeneratorexploitation",
            "loc_on_board",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitationofgtg",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitationofgtg",
            "nomenclature",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitationofgtg",
            "eqpt_code",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "reductiongearexploitationofgtg",
            "loc_on_board",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "replacementofmajorassembliesofgtg",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "replacementofmajorassembliesofgtg",
            "eqpt_sr_number",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "annualsrmrroutineundertakenofgtg",
            "undertaken_by_whom",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "rhextension",
            "eqpt_name",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "rhextension",
            "nomenclature",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "rhextension",
            "loc_on_board",
            models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AddField(
            "rhextension",
            "on_routine_text",
            models.CharField(blank=True, max_length=250, null=True),
        ),
    ]
