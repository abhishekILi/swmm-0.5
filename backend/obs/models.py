from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from users.models import CustomUserProfile

from .managers import BaseManager
from .utils import spare_image_upload_path


class UppercaseCleanMixin:
    uppercase_fields = ()

    def clean(self):
        super().clean()
        for field_name in self.uppercase_fields:
            value = getattr(self, field_name, None)
            if isinstance(value, str):
                setattr(self, field_name, value.upper())

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SpareClass(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    name = models.CharField(max_length=100)
    department = models.ForeignKey(
        "master.Department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="onboard_spare_classes",
    )

    uppercase_fields = ("name",)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "department")

    def __str__(self):
        return self.name


class EquipmentClass(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    name = models.CharField(max_length=100)
    spare_class = models.ForeignKey(
        SpareClass,
        on_delete=models.PROTECT,
        related_name="equipment_classes",
    )

    uppercase_fields = ("name",)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "spare_class")

    def __str__(self):
        return self.name


class Denomination(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    name = models.CharField(max_length=100, default="")
    department = models.ForeignKey(
        "master.Department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="onboard_denominations",
    )

    uppercase_fields = ("name",)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "department")

    def __str__(self):
        return self.name


class Authority(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    name = models.CharField(max_length=100, unique=True)

    uppercase_fields = ("name",)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Spares(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    PERMANENT = "PERMANENT"
    RETURNABLE = "RETURNABLE"
    CONSUMABLE = "CONSUMABLE"

    CATEGORY_CHOICES = [
        (PERMANENT, "PERMANENT"),
        (RETURNABLE, "RETURNABLE"),
        (CONSUMABLE, "CONSUMABLE"),
    ]

    equipment_class = models.ForeignKey(
        EquipmentClass,
        on_delete=models.PROTECT,
        related_name="spares",
    )
    pattern_number = models.SlugField(max_length=500, default="", blank=True)
    description = models.CharField(max_length=1000, default="")
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=PERMANENT,
    )
    critical = models.BooleanField(default=False, blank=True)
    compartment = models.CharField(
        max_length=200,
        default="UNKNOWN",
        null=True,
        blank=True,
    )
    location = models.CharField(
        max_length=200,
        default="UNKNOWN",
        null=True,
        blank=True,
    )
    rack_position = models.CharField(
        max_length=200,
        default="UNKNOWN",
        null=True,
        blank=True,
    )
    rack_number = models.CharField(
        max_length=200,
        default="UNKNOWN",
        null=True,
        blank=True,
    )
    denomination = models.ForeignKey(
        Denomination,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="spares",
    )
    quantity_authorised = models.PositiveSmallIntegerField(default=0, blank=True)
    quantity_available = models.PositiveSmallIntegerField(default=0, blank=True)
    authority = models.ForeignKey(
        Authority,
        on_delete=models.PROTECT,
        related_name="spares",
    )
    page = models.SlugField(max_length=200, default="", null=True, blank=True)
    line = models.CharField(max_length=200, default="", null=True, blank=True)
    remarks = models.TextField(
        max_length=2000,
        default="",
        null=True,
        blank=True,
    )
    mo_demand_number = models.CharField(
        max_length=200,
        default="",
        null=True,
        blank=True,
    )
    image = models.ImageField(
        upload_to=spare_image_upload_path,
        default="obs/default.png",
        max_length=500,
        null=True,
        blank=True,
    )
    is_obs = models.BooleanField(default=False, null=True)

    uppercase_fields = (
        "pattern_number",
        "description",
        "category",
        "compartment",
        "location",
        "rack_position",
        "rack_number",
        "page",
        "line",
        "remarks",
        "mo_demand_number",
    )

    class Meta:
        ordering = ["pattern_number"]

    def clean(self):
        super().clean()
        if self.quantity_available > self.quantity_authorised:
            raise ValidationError(
                {
                    "quantity_available": (
                        "Available quantity cannot exceed authorised quantity."
                    )
                }
            )

    def __str__(self):
        return f"{self.pattern_number} - {self.description}"


class RoutineSpareUsage(models.Model):
    objects = BaseManager()
    routine = models.ForeignKey(
        "ems.AddRoutineDetails",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="onboard_spare_usages",
    )
    routine_description = models.ForeignKey(
        "ems.RoutineDescription",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="onboard_spare_usages",
    )
    spare = models.ForeignKey(
        Spares,
        on_delete=models.CASCADE,
        related_name="routine_usages",
    )
    quantity_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
    )
    date_used = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-date_used", "-id"]

    def __str__(self):
        return f"{self.spare.pattern_number} used in routine"


class Issue(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="issues",
    )
    equipment = models.ForeignKey(
        "ems.EquipmentName",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="onboard_spare_issues",
    )
    date_of_issue = models.DateField(
        default=timezone.now,
        verbose_name="Date of Issue",
    )
    username = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        related_name="onboard_spare_issues",
    )
    quantity_issued = models.PositiveSmallIntegerField(default=0)
    issue_time = models.DateTimeField(auto_now_add=True, null=True)
    remarks = models.CharField(max_length=200, default="", blank=True)
    dart_number = models.CharField(max_length=200, default="", blank=True)
    is_return = models.BooleanField(default=False, blank=True)
    is_wed_mo = models.BooleanField(default=False, blank=True)
    is_deleted = models.BooleanField(default=False, blank=True)

    uppercase_fields = ("remarks", "dart_number")

    class Meta:
        ordering = ["-date_of_issue", "-id"]

    def clean(self):
        super().clean()
        if self.spare_id and self.quantity_issued > self.spare.quantity_available:
            raise ValidationError(
                {
                    "quantity_issued": (
                        "Issue quantity cannot exceed available quantity."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            spare = Spares.objects.select_for_update().get(pk=self.spare_id)
            if self.quantity_issued > spare.quantity_available:
                raise ValidationError(
                    {
                        "quantity_issued": (
                            "Issue quantity cannot exceed available quantity."
                        )
                    }
                )

            self.spare = spare
            response = super().save(*args, **kwargs)
            spare.quantity_available -= self.quantity_issued
            spare.save(update_fields=["quantity_available"])
            return response

    def __str__(self):
        return f"{self.spare.pattern_number} issued {self.quantity_issued}"


class IssueList(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.PROTECT,
        related_name="issue_list_entries",
    )
    quantity_toreturn = models.PositiveSmallIntegerField(default=0)
    dart_number = models.CharField(max_length=200, default="", blank=True)

    uppercase_fields = ("dart_number",)

    def __str__(self):
        return f"{self.issue_entry} return qty {self.quantity_toreturn}"


class Return(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    spare_id = models.ForeignKey(
        Spares,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="returns",
    )
    command_id = models.ForeignKey(
        "master.MShipCommand",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="onboard_spare_returns",
    )
    ship = models.ForeignKey(
        "master.Ship",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="onboard_spare_returns",
        db_column="ship_id",
    )
    username = models.CharField(max_length=200, default="", blank=True)
    returned_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="onboard_spare_returns",
    )
    remarks = models.TextField(
        max_length=2000,
        default="",
        null=True,
        blank=True,
    )
    quantity_returned = models.PositiveSmallIntegerField(default=0)
    return_time = models.DateTimeField(auto_now_add=True, null=True)

    uppercase_fields = ("username", "remarks")

    class Meta:
        ordering = ["-return_time", "-id"]

    def save(self, *args, **kwargs):
        if self.pk is not None or not self.spare_id_id:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            spare = Spares.objects.select_for_update().get(pk=self.spare_id_id)
            updated_quantity = spare.quantity_available + self.quantity_returned
            if updated_quantity > spare.quantity_authorised:
                raise ValidationError(
                    {
                        "quantity_returned": (
                            "Returned quantity would exceed authorised stock."
                        )
                    }
                )

            self.spare_id = spare
            response = super().save(*args, **kwargs)
            spare.quantity_available = updated_quantity
            spare.save(update_fields=["quantity_available"])
            quantity_to_adjust = self.quantity_returned
            issue_entries = (
                IssueList.objects.select_for_update()
                .filter(issue_entry__spare=spare)
                .order_by("id")
            )
            for issue_entry in issue_entries:
                if quantity_to_adjust <= 0:
                    break
                if quantity_to_adjust >= issue_entry.quantity_toreturn:
                    quantity_to_adjust -= issue_entry.quantity_toreturn
                    issue_entry.delete()
                else:
                    issue_entry.quantity_toreturn -= quantity_to_adjust
                    issue_entry.save(update_fields=["quantity_toreturn"])
                    break
            return response

    def __str__(self):
        spare = self.spare_id.pattern_number if self.spare_id else "No spare"
        return f"{spare} returned {self.quantity_returned}"


class Survey(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="surveys",
    )
    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="surveys",
    )
    quantity_tosurvey = models.PositiveSmallIntegerField(default=0)
    dart_number = models.TextField(null=True, blank=True)
    is_iif = models.BooleanField(default=False, blank=True)
    is_iif_sync = models.BooleanField(default=False, blank=True)

    uppercase_fields = ("dart_number",)

    def __str__(self):
        return f"{self.spare.pattern_number} survey {self.quantity_tosurvey}"


class PostSurvey(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    NORMAL = "NORMAL"
    OPDEM = "OPDEM"
    PTS = "PTS"
    STOREDEM = "STOREDEM"
    ONE_TIME_APPROVAL = "ONE_TIME_APPROVAL"

    SURVEY_TYPE_CHOICES = [
        (NORMAL, "Normal Survey"),
        (OPDEM, "Operational Demand"),
        (PTS, "Provisioning Technical Specification"),
        (STOREDEM, "Store Demand"),
        (ONE_TIME_APPROVAL, "One-Time Approval"),
    ]

    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="post_surveys",
    )
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="post_surveys",
    )
    quantity_surveyed = models.PositiveSmallIntegerField(default=0)
    survey_type = models.CharField(
        max_length=30,
        choices=SURVEY_TYPE_CHOICES,
        default=NORMAL,
    )
    survey_number = models.SlugField(max_length=50, default="NA", blank=True)
    survey_report_date = models.DateTimeField(null=True, blank=True)
    remarks = models.CharField(max_length=200, default="", blank=True)
    has_pts = models.BooleanField(default=False, blank=True)
    created_by = models.CharField(max_length=200, default="", blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_onboard_post_surveys",
    )
    dart_number = models.TextField(null=True, blank=True)

    uppercase_fields = ("survey_number", "remarks", "created_by", "dart_number")

    def __str__(self):
        return self.survey_number


class Demand(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="demands",
    )
    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="demands",
    )
    quantity_todemand = models.PositiveSmallIntegerField(default=0)
    survey_entry = models.ForeignKey(
        PostSurvey,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="demands",
    )
    dart_number = models.TextField(null=True, blank=True)
    is_iif = models.BooleanField(default=False, blank=True)
    is_iif_sync = models.BooleanField(default=False, blank=True)

    uppercase_fields = ("dart_number",)

    def __str__(self):
        return f"{self.spare.pattern_number} demand {self.quantity_todemand}"


class PostDemand(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="post_demands",
    )
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="post_demands",
    )
    quantity_demanded = models.PositiveSmallIntegerField(default=0)
    demand_number = models.SlugField(max_length=50, default="", blank=True)
    demand_date = models.DateTimeField(null=True, blank=True)
    remarks = models.CharField(max_length=200, default="", blank=True)
    created_by = models.CharField(max_length=200, default="", blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_onboard_post_demands",
    )
    dart_number = models.TextField(null=True, blank=True)

    uppercase_fields = ("demand_number", "remarks", "created_by", "dart_number")

    def __str__(self):
        return self.demand_number


class Receive(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="receives",
    )
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="receives",
    )
    quantity_toreceive = models.PositiveSmallIntegerField(default=0)
    demand_entry = models.ForeignKey(
        PostDemand,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="receives",
    )
    dart_number = models.TextField(null=True, blank=True)

    uppercase_fields = ("dart_number",)

    def __str__(self):
        return f"{self.spare.pattern_number} receive {self.quantity_toreceive}"


class PostReceive(UppercaseCleanMixin, models.Model):
    objects = BaseManager()
    NAC_STATUS_CHOICES = [
        (False, "NO"),
        (True, "YES"),
    ]

    spare = models.ForeignKey(
        Spares,
        on_delete=models.PROTECT,
        related_name="post_receives",
    )
    issue_entry = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="post_receives",
    )
    quantity_received = models.PositiveSmallIntegerField(default=0)
    receipt_number = models.SlugField(max_length=50, default="", blank=True)
    receive_date = models.DateTimeField(null=True, blank=True)
    nac_status = models.BooleanField(
        choices=NAC_STATUS_CHOICES,
        default=False,
        blank=True,
    )
    remarks = models.CharField(max_length=200, default="", blank=True)
    dart_number = models.TextField(null=True, blank=True)
    created_by = models.CharField(max_length=200, default="", blank=True)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_onboard_post_receives",
    )

    uppercase_fields = (
        "receipt_number",
        "remarks",
        "dart_number",
        "created_by",
    )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            spare = Spares.objects.select_for_update().get(pk=self.spare_id)
            updated_quantity = spare.quantity_available + self.quantity_received
            if updated_quantity > spare.quantity_authorised:
                raise ValidationError(
                    {
                        "quantity_received": (
                            "Received quantity would exceed authorised stock."
                        )
                    }
                )

            self.spare = spare
            response = super().save(*args, **kwargs)
            spare.quantity_available = updated_quantity
            spare.save(update_fields=["quantity_available"])
            return response

    def __str__(self):
        return self.receipt_number


class PlannedRoutineSpareList(models.Model):
    objects = BaseManager()
    pattern_number = models.CharField(max_length=200, default="", blank=True)
    planned_routine_description = models.ForeignKey(
        "ems.PlannedRoutineDescription",
        on_delete=models.CASCADE,
        related_name="onboard_spare_lists",
    )
    quantity_required = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "obs_planned_routine_spare_list"
        ordering = ["pattern_number"]

    def __str__(self):
        return self.pattern_number


class SparesMapping(models.Model):
    objects = BaseManager()
    equipment_class = models.ForeignKey(
        EquipmentClass,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="spares_mappings",
    )
    equipment = models.ForeignKey(
        "sfd.ShipEquipment",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="obs_mappings",
    )
    section_name = models.ForeignKey(
        "master.Section",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="obs_mappings",
    )

    def __str__(self):
        equipment_class = self.equipment_class or "No equipment class"
        equipment = self.equipment or "No equipment"
        return f"{equipment_class} -> {equipment}"


class NotInCattedItem(models.Model):
    objects = BaseManager()
    spare_id = models.ForeignKey(
        Spares,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="not_in_catted_items",
    )
    incatted_status = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        spare = self.spare_id.pattern_number if self.spare_id else "No spare"
        return f"{spare} not in catted"
