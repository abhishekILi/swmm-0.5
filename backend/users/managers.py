from django.contrib.auth.models import BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, username, user_profile, password=None):
        if not username:
            raise ValueError("Username must not be blank.")
        user = self.model(username=username, user_profile_id=user_profile)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, user_profile, password=None):
        user = self.create_user(username, user_profile=user_profile, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user
