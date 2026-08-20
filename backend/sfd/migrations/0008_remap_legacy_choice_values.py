from django.db import migrations

UPPER_DECK_MAP = {f"{i:02d}": f"deck{i:02d}" for i in range(1, 11)}
LOWER_DECK_MAP = {str(i): f"deck{i}" for i in range(1, 11)}
LOCATION_MAP = {
    "Port, Aft": "port_aft",
    "Port, Forward": "port_forward",
    "Starboard, Forward": "starboard_forward",
    "Starboard, Aft": "starboard_aft",
}
CATEGORY_MAP = {"local_purchase": "other"}


def forwards(apps, schema_editor):
    CompartmentMaster = apps.get_model("sfd", "CompartmentMaster")
    for old, new in UPPER_DECK_MAP.items():
        CompartmentMaster.objects.filter(upper_deck=old).update(upper_deck=new)
    for old, new in LOWER_DECK_MAP.items():
        CompartmentMaster.objects.filter(lower_deck=old).update(lower_deck=new)
    for old, new in LOCATION_MAP.items():
        CompartmentMaster.objects.filter(location=old).update(location=new)

    ShipEquipment = apps.get_model("sfd", "ShipEquipment")
    for old, new in CATEGORY_MAP.items():
        ShipEquipment.objects.filter(category=old).update(category=new)


def backwards(apps, schema_editor):
    CompartmentMaster = apps.get_model("sfd", "CompartmentMaster")
    for old, new in UPPER_DECK_MAP.items():
        CompartmentMaster.objects.filter(upper_deck=new).update(upper_deck=old)
    for old, new in LOWER_DECK_MAP.items():
        CompartmentMaster.objects.filter(lower_deck=new).update(lower_deck=old)
    for old, new in LOCATION_MAP.items():
        CompartmentMaster.objects.filter(location=new).update(location=old)

    ShipEquipment = apps.get_model("sfd", "ShipEquipment")
    for old, new in CATEGORY_MAP.items():
        ShipEquipment.objects.filter(category=new).update(category=old)


class Migration(migrations.Migration):
    dependencies = [
        ("sfd", "0007_equipment_authority_equipment_manufacturer_name_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
