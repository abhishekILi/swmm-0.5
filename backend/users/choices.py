access_level_choices = [
    # first letter goes into the database , and second letter is for forms.py to show
    ("0", "ADMINISTRATOR"),
    ("1", "SUPERUSER"),
    ("2", "STOREKEEPER"),
    ("3", "OTHERS"),
]

category_choices = [
    ("PERMANENT", "PERMANENT"),
    ("RETURNABLE", "RETURNABLE"),
    ("CONSUMABLE", "CONSUMABLE"),
]

nac_status_choices = [
    # first letter goes into the database , and second letter is for forms.py to show in html
    (False, "NO"),
    (True, "YES"),
]
