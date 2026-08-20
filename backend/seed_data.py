import argparse
import os
import sys
from pathlib import Path

import django
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection, transaction

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swmm.settings")
django.setup()

User = get_user_model()

try:
    from users.models import CustomUserProfile
except (ImportError, AttributeError):
    CustomUserProfile = None

SEED_PASS = "12345"
SYSTEM_IP = "127.0.0.1"

PROJECT_APP_LABELS = {
    "activity_planner",
    "dart",
    "crew_manage",
    "dl_monitor",
    "dms",
    "ems",
    "hotwork",
    "ilms",
    "inout_tag",
    "master",
    "obs",
    "refit",
    "srar",
    "tank",
    "ticket_manage",
    "users",
    "wlms",
    "work_manage",
}


def table_exists(model):
    if not model:
        return False
    return model._meta.db_table in connection.introspection.table_names()


def is_project_model(model):
    return model._meta.app_label in PROJECT_APP_LABELS and table_exists(model)


def project_models():
    return [model for model in apps.get_models() if is_project_model(model)]


def clear_seeded_data():
    with connection.cursor() as cursor:
        names = [
            f'"{model._meta.db_table}"'
            for model in project_models()
            if not model._meta.auto_created
        ]
        if names:
            cursor.execute(
                f"TRUNCATE TABLE {', '.join(names)} RESTART IDENTITY CASCADE;"
            )
    print("Cleared project database tables.")


def seed_users_only():
    usernames = [
        "1234",
        "shipadmin",
        "co",
        "DyHOD",
        "Admin",
        "Maintainer",
        "Storekeeper",
    ]
    for index, raw_username in enumerate(usernames, 1):
        username = raw_username.upper()

        # Create minimal profile
        profile = None
        if CustomUserProfile and table_exists(CustomUserProfile):
            personal_number = f"PN{index:04d}"
            # Ensure no conflicting profile exists
            CustomUserProfile.objects.filter(personal_number=personal_number).delete()
            profile = CustomUserProfile.objects.create(
                personal_number=personal_number,
                firstname=raw_username,
                lastname="User",
                has_credentials=True,
                user_active=True,
                access_level="0"
                if raw_username in ("1234", "shipadmin", "co")
                else "2",
            )

        # Ensure no conflicting user exists
        User.objects.filter(username__iexact=username).delete()

        user_defaults = {
            "is_active": True,
            "is_admin": raw_username in ("1234", "shipadmin", "co"),
        }
        if profile:
            user_defaults["user_profile"] = profile

        user = User.objects.create(username=username, **user_defaults)
        user.set_password(SEED_PASS)
        user.save()
        print(f"Created user: {username}")


def main():
    parser = argparse.ArgumentParser(
        description="Seed SWMM backend with minimal User credentials."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear seeded demo tables before inserting.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Ignored (kept for backward compatibility).",
    )
    args = parser.parse_args()

    with transaction.atomic():
        if args.clear:
            clear_seeded_data()
        seed_users_only()

    print("Seed completed.")
    print(
        "Superuser usernames: 1234, shipadmin, co, DyHOD, Admin, Maintainer, Storekeeper"
    )
    print("Password for all seeded users: 12345")


if __name__ == "__main__":
    main()
