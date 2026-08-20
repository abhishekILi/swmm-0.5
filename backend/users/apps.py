from django.apps import AppConfig


class UserDrfConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"
    verbose_name = "Users API (DRF)"
