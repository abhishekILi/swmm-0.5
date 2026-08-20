# Create your models here.
from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils.timezone import now

from master.models import Department, MasterCommand
from users.choices import access_level_choices
from users.managers import CustomUserManager


class UserDepartment(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)


class Designation(models.Model):
    id = models.BigAutoField(primary_key=True)
    designation_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.designation_name}"


class Rank(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, default="")
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, null=True, blank=True
    )

    def __str__(self):
        return f"{self.name}"


class RoleMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    role_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.role_name}"


class Role(models.Model):
    id = models.BigAutoField(primary_key=True)
    role_name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.role_name}"


class CustomUserProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    rank = models.ForeignKey(Rank, on_delete=models.PROTECT, null=True, blank=True)
    firstname = models.CharField(max_length=100, default="")
    lastname = models.CharField(max_length=100, blank=True, default="")
    designation_master = models.ForeignKey(
        Designation, on_delete=models.PROTECT, null=True, blank=True
    )
    designation = models.CharField(max_length=100, blank=True, default="", null=True)
    personal_number = models.SlugField(max_length=15, default="")
    section = models.CharField(max_length=50, blank=True, default="")
    ship_joining_date = models.DateTimeField(default=now, null=True)
    ship_leaving_date = models.DateTimeField(null=True)
    remarks = models.CharField(max_length=200, default="")
    access_level = models.CharField(
        max_length=20, default="2", null=True, choices=access_level_choices
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, null=True, blank=True
    )
    executive_sub_department = models.CharField(
        max_length=100, blank=True, default="", null=True
    )
    role_master = models.ForeignKey(
        Role, on_delete=models.PROTECT, null=True, blank=True
    )
    command_name = models.ForeignKey(
        MasterCommand,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="user_command",
    )
    ship = models.ForeignKey(
        "master.Ship", on_delete=models.PROTECT, null=True, blank=True
    )
    has_credentials = models.BooleanField(default=False, null=True)
    is_role = models.BooleanField(default=False, null=True)
    user_created_on = models.DateTimeField(auto_now_add=True, null=True)
    user_active = models.BooleanField(default=True)
    is_ood = models.BooleanField(default=False, null=True, blank=True)
    is_regulator = models.BooleanField(default=False, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)

    # --- NEW COLUMNS ADDED HERE ---
    is_married = models.BooleanField(default=False, null=True, blank=True)
    marriage_date = models.DateField(null=True, blank=True)
    division = models.ForeignKey(
        "MasterRegulatorDivision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sailors",
    )

    class Meta:
        unique_together = (
            "personal_number",
            "ship_joining_date",
        )

    # changes this function

    def clean(self):
        if self.firstname:
            self.firstname = self.firstname.capitalize()

        if self.lastname:
            self.lastname = self.lastname.capitalize()

        if self.personal_number:
            self.personal_number = self.personal_number.upper()

        if self.section:
            self.section = self.section.upper()

        if self.designation:
            self.designation = self.designation.upper()

        if self.remarks:
            self.remarks = self.remarks.upper()

        if self.marriage_date:
            self.marriage_date = True

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.personal_number})"


class CustomUser(AbstractBaseUser):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    user_profile = models.ForeignKey(
        CustomUserProfile, on_delete=models.PROTECT, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    objects = CustomUserManager()

    REQUIRED_FIELDS = ("user_profile",)
    USERNAME_FIELD = "username"

    def __str__(self):
        return self.username

    @property
    def CustomUser_profile(self):
        return self.user_profile

    @property
    def department(self):
        return self.user_profile.department if self.user_profile_id else None

    @property
    def department_id(self):
        return self.user_profile.department_id if self.user_profile_id else None

    def get_full_name(self):
        if not self.user_profile_id:
            return self.username

        full_name = (
            f"{self.user_profile.firstname or ''} {self.user_profile.lastname or ''}"
        ).strip()
        return full_name or self.username

    def get_short_name(self):
        if self.user_profile_id and self.user_profile.firstname:
            return self.user_profile.firstname
        return self.username

    def has_perm(self, perm, object=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin

    def clean(self):
        self.username = self.username.upper()


class role_hierarchy(models.Model):
    id = models.IntegerField(primary_key=True)  # ✅ manual ID
    role_name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "role_hierarchy"  # ✅ custom table name
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return f"{self.id} - {self.role_name}"


class OtherCustomUserProfile(models.Model):
    id = models.BigAutoField(primary_key=True)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    personal_number = models.CharField(max_length=50, unique=True)
    rank = models.ForeignKey(Rank, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    designation = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    access_level = models.CharField(
        max_length=2, choices=access_level_choices, default="3"
    )

    created_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_profiles",
    )

    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.get_access_level_display()})"


# --- Know Your Regulator Models ---


class MasterRegulatorDivision(models.Model):
    id = models.BigAutoField(primary_key=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True
    )
    regulator = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.CASCADE,
        related_name="regulator_divisions",
    )
    division = models.CharField(max_length=255)

    class Meta:
        db_table = "master_regulator_division"

    def __str__(self):
        return f"{self.division} ({self.regulator.firstname})"


class MasterKnowYourRegulator(models.Model):
    id = models.BigAutoField(primary_key=True)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True
    )
    regulator = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.CASCADE,
        related_name="know_regulator",
    )
    # division = models.ForeignKey(MasterRegulatorDivision, on_delete=models.CASCADE) #NOSONAR
    # sailors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='sailor_regulator')
    sailor = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="division_sailor",
    )

    division = models.ForeignKey(
        MasterRegulatorDivision, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "master_know_your_regulator"

    def __str__(self):
        return f"{self.department.name} - {self.regulator.firstname} - {self.division.division}"


# Add this to your models.py file


class LoginRegistrationImage(models.Model):
    """
    Stores images to be displayed on the login/registration page
    """

    id = models.BigAutoField(primary_key=True)

    image = models.ImageField(
        upload_to="login_images/", help_text="Upload login page image"
    )
    name = models.CharField(
        max_length=255, blank=True, null=True, help_text="Optional image name"
    )
    source = models.CharField(max_length=100, default="login-registration-image")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_login_images",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "login_registration_images"
        ordering = ("-uploaded_at",)
        verbose_name = "Login Registration Image"
        verbose_name_plural = "Login Registration Images"

    def __str__(self):
        return f"Login Image - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"


class GalleryImage(models.Model):
    id = models.BigAutoField(primary_key=True)
    image = models.ImageField(upload_to="gallery/")
    title = models.CharField(max_length=200)
    caption = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    ship = models.ForeignKey(
        "master.Ship", on_delete=models.PROTECT, null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, null=True, blank=True
    )

    def __str__(self):
        return self.title
