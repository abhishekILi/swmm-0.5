from django.db import models
from django.utils import timezone

from master.models import Base, Department
from sfd.models import ShipEquipment

UserProfile = "users.CustomUserProfile"


class TypeChoices(models.TextChoices):
    DANGER = "danger", "Danger"
    WARNING = "warning", "Warning"


class ConditionChoices(models.TextChoices):
    OPS = "ops", "Ops"
    NON_OPS = "non_ops", "Non Ops"
    PARTIALLY_OPS = "partially_ops", "Partially Ops"


class ApprovalStatusChoices(models.TextChoices):
    PENDING = "pending", "Pending CO Approval"
    PENDING_HOD = "pending_hod", "Pending HOD Approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class TagOutReasonChoices(models.TextChoices):
    TY_LOAN_RTLAPP = "ty_loan_rtlapp", "Ty Loan/RTLAPP"
    SURVEY_AND_DEMAND = "survey_and_demand", "Survey & Demand"
    REPAIR_OR_OVERHAULING = "repair_or_overhauling", "Repair/Overhauling"
    CONSUMABLE_SURVERY = "consumable_survery", "Consumable Survey"
    ABER_REPLACEMENT = "aber_replacement", "ABER Replacement"


class StatusChoices(models.TextChoices):
    COMPLETED = "completed", "Completed"
    IN_PROGRESS = "in_progress", "In Progress"
    PENDING = "pending", "Pending"


class TagOut(Base):
    id = models.BigAutoField(primary_key=True)
    tagout_number = models.CharField(
        max_length=50, unique=True, editable=False, null=True, blank=True
    )
    date = models.DateField(null=True, blank=True)
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="tagouts",
        null=True,
        blank=True,
    )
    tagout_equipment_name = models.ForeignKey(
        ShipEquipment,
        on_delete=models.CASCADE,
        related_name="tagout_equipment",
        null=True,
        blank=True,
    )
    name_of_subsystem = models.CharField(max_length=255, null=True, blank=True)
    name_of_component = models.CharField(max_length=255, null=True, blank=True)
    serial_number_of_component = models.CharField(max_length=255, null=True, blank=True)
    pattern_number_of_component = models.CharField(
        max_length=255, null=True, blank=True
    )
    weight_of_component = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    type = models.CharField(
        max_length=20, choices=TypeChoices.choices, default="danger"
    )
    condition = models.CharField(
        max_length=20, choices=ConditionChoices.choices, null=True, blank=True
    )
    special_instructions = models.TextField(blank=True, null=True)

    departments_affected = models.ManyToManyField(
        Department, related_name="affected_tagouts"
    )
    expected_date_of_tagin = models.DateField(null=True, blank=True)
    tagout_reason = models.CharField(
        max_length=30, choices=TagOutReasonChoices.choices, null=True, blank=True
    )
    tagout_description = models.TextField(blank=True, null=True)
    tagout_maintainer_name_rank = models.CharField(
        max_length=255, null=True, blank=True
    )

    ty_loan_ship = models.CharField(max_length=255, blank=True, null=True)
    ty_authority = models.CharField(max_length=255, blank=True, null=True)
    ty_item_taken_by = models.CharField(max_length=255, blank=True, null=True)
    ty_additional_items = models.TextField(blank=True, null=True)

    survery_demand_authority = models.CharField(max_length=255, blank=True, null=True)

    repair_ra_number = models.CharField(max_length=255, blank=True, null=True)
    repair_landed_details = models.TextField(blank=True, null=True)
    repair_item_taken_by = models.CharField(max_length=255, blank=True, null=True)
    repair_additional_items = models.TextField(blank=True, null=True)

    aber_authority = models.CharField(max_length=255, blank=True, null=True)
    replacement_item = models.CharField(max_length=255, blank=True, null=True)
    estimated_bom_arrival_date = models.DateField(blank=True, null=True)

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatusChoices.choices,
        default="in_progress",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_tagouts",
    )
    approved_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "inout_tagout"
        ordering = ("-created_on",)

    def save(self, *args, **kwargs):
        if not self.tagout_number:
            year = timezone.now().year
            last_tagout = (
                TagOut.objects.filter(tagout_number__startswith=f"TAG-{year}-")
                .order_by("-tagout_number")
                .first()
            )

            if last_tagout:
                last_serial = int(last_tagout.tagout_number.split("-")[-1])
                new_serial = last_serial + 1
            else:
                new_serial = 1

            self.tagout_number = f"TAG-{year}-{new_serial:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tagout_number} - {self.tagout_equipment_name}"


class TagIn(Base):
    id = models.BigAutoField(primary_key=True)
    tagout = models.OneToOneField(
        TagOut, on_delete=models.CASCADE, related_name="tagin"
    )
    tagin_date = models.DateField(default=timezone.now)
    tagin_description = models.TextField(default="", blank=True)
    tagin_maintainer = models.CharField(max_length=255, default="", blank=True)
    all_items_returned = models.BooleanField(default=True)
    items_pending = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default="pending"
    )

    # Approval fields
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatusChoices.choices,
        default="pending",
        null=True,
        blank=True,
    )
    tagin_remarks = models.TextField(blank=True, null=True)
    tagin_maintainer_name_rank = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "inout_tagin"
        ordering = ("-created_on",)

    def __str__(self):
        return f"TagIn for {self.tagout.tagout_number}"

    def check_all_approvals(self):
        """Check if all HODs have approved and update overall approval status."""
        approvals = self.tagin_approvals.filter(active=1)
        if not approvals.exists():
            return

        # Check if any rejection
        if approvals.filter(approval_status="rejected").exists():
            self.approval_status = "rejected"
        # Check if all approved
        elif approvals.filter(approval_status="approved").count() == approvals.count():
            self.approval_status = "approved"
            self.status = "completed"
        else:
            self.approval_status = "pending_hod"
            self.status = "in_progress"

        self.save()


class TagInApproval(Base):
    """Track individual HOD approvals for Tag In."""

    id = models.BigAutoField(primary_key=True)

    tagin = models.ForeignKey(
        TagIn, on_delete=models.CASCADE, related_name="tagin_approvals"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="tagin_approvals",
        null=True,
        blank=True,
    )
    approval_status = models.CharField(
        max_length=20, choices=ApprovalStatusChoices.choices, default="pending"
    )
    approved_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_tagins",
    )
    approved_on = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "inout_tagin_approval"
        ordering = ("-created_on",)
        unique_together = ("tagin", "department")

    def __str__(self):
        return (
            f"Approval for {self.tagin.tagout.tagout_number} - {self.department.name}"
        )
