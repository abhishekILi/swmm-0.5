from django.db import models

from master.models import Department, SubDepartment
from users.models import CustomUserProfile


class HotworkType(models.TextChoices):
    CUTTING = "CUTTING", "Cutting"
    WELDING = "WELDING", "Welding"
    CUTTING_WELDING = "CUTTING_WELDING", "Cutting + Welding"
    GRINDING = "GRINDING", "Grinding"


class DayType(models.TextChoices):
    HOLIDAY = "HOLIDAY", "Holiday"
    WORKING_DAY = "WORKING_DAY", "Working Day"


class ApprovalStatus(models.TextChoices):
    PENDING_INCHARGE = "pending_incharge", "Not Started"
    PENDING_DYHOD = "pending_dyhod", "Initiated"
    PENDING_FIRST_HOD = "pending_first_hod", "Not Started"
    PENDING_HODS = "pending_hods", "Initiated"
    PENDING_OOD = "pending_ood", "Initiated"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class YesNoChoices(models.TextChoices):
    YES = "YES", "Yes"
    NO = "NO", "No"


class OpsNonOpsChoices(models.TextChoices):
    OPS = "OPS", "Operational"
    NON_OPS = "NON_OPS", "Non Operational"


class ProgressAction(models.TextChoices):
    STARTED = "started", "Started"
    PAUSED = "paused", "Paused"
    RESUMED = "resumed", "Resumed"
    COMPLETED = "completed", "Completed"


class AddHotwork(models.Model):
    id = models.BigAutoField(primary_key=True)
    holiday_or_working_day = models.CharField(
        max_length=20,
        choices=DayType.choices,
        default=DayType.WORKING_DAY,
        blank=True,
        null=True,
    )

    hotwork_code = models.CharField(max_length=50, blank=True, null=True)
    date_of_hotwork = models.DateField(db_index=True)

    sub_department = models.ForeignKey(
        SubDepartment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    sentries_required = models.BooleanField(default=True)
    previous_hotwork_code = models.CharField(max_length=50, blank=True, null=True)
    location_of_hotwork = models.CharField(max_length=200)
    type_of_hotwork = models.CharField(
        max_length=50,
        choices=HotworkType.choices,
    )

    departmental_officer = models.CharField(max_length=120, blank=True, null=True)
    all_adjacent_compartments = models.CharField(max_length=255, blank=True, null=True)
    sentry_names = models.TextField(blank=True, null=True)

    hotwork_incharge = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hotwork_incharge",
    )
    dl_number = models.CharField(max_length=120, blank=True, null=True)
    supervision_welder_name = models.CharField(max_length=120, blank=True, null=True)

    manager_of_concern_center = models.CharField(max_length=120, blank=True, null=True)
    officer_of_the_day = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="officer_of_the_day",
    )
    remarks = models.TextField(blank=True, null=True)
    night_work = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    created_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_hotworks",
    )

    # Approval workflow fields

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING_INCHARGE,
        db_index=True,
    )

    # Incharge approval (selected during hotwork creation)
    incharge_approved = models.BooleanField(default=False)
    incharge_approved_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incharge_approved_hotworks",
    )
    incharge_approved_at = models.DateTimeField(null=True, blank=True)

    # DYHOD (Department Officer) approval - same department as creator
    dyhod_approved = models.BooleanField(default=False)
    dyhod_approved_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dyhod_approved_hotworks",
    )
    dyhod_approved_at = models.DateTimeField(null=True, blank=True)

    # Overall HOD approval status
    all_hods_approved = models.BooleanField(default=False)

    # Officer of the Day (OOD) approval - final approval step
    ood_approved = models.BooleanField(default=False)
    ood_approved_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ood_approved_hotworks",
    )
    ood_approved_at = models.DateTimeField(null=True, blank=True)

    # Hotwork progress tracking
    is_started = models.BooleanField(default=False)
    started_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_hotworks",
    )
    started_at = models.DateTimeField(null=True, blank=True)

    is_paused = models.BooleanField(default=False)
    paused_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paused_hotworks",
    )
    paused_at = models.DateTimeField(null=True, blank=True)
    pause_reason = models.TextField(blank=True, null=True)

    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_hotworks",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_remarks = models.TextField(blank=True, null=True)

    def check_all_hods_approved(self):
        """Check if all required HODs have approved and update to pending OOD status"""
        required_department_ids = [2, 3, 5]  # ENGINEERING, ELECTRICAL, NBCD

        approved_count = self.hod_approvals.filter(
            department_id__in=required_department_ids, approved=True
        ).count()

        # If this was HOD-initiated and first HOD just approved, change status to 'Initiated'
        if self.approval_status == "pending_first_hod" and approved_count == 1:
            self.approval_status = "pending_hods"
            self.save()
            return False

        # Check if all HODs have approved
        if approved_count == len(required_department_ids):
            self.all_hods_approved = True
            self.approval_status = "pending_ood"
            self.save()
            return True
        return False

    @property
    def current_status(self):
        """Return the current status of the hotwork with appropriate display value"""
        if self.is_completed:
            return "Completed"
        return self.get_approval_status_display()

    # Helper methods for Fire & Safety template to get approval data by department
    def get_approval_by_department(self, dept_id):
        """Get HOD approval record for a specific department, or None if not found"""
        return self.hod_approvals.filter(department_id=dept_id).first()

    def get_eng_approval(self):
        """Get Engineering Officer (Dept 2) approval"""
        return self.get_approval_by_department(2)

    def get_elec_approval(self):
        """Get Electrical Officer (Dept 3) approval"""
        return self.get_approval_by_department(3)

    def get_nbcdo_approval(self):
        """Get NBCDO Officer (Dept 5) approval"""
        return self.get_approval_by_department(5)

    class Meta:
        db_table = "Hotwork_addhotwork"
        ordering = ("-created_at",)


class HotworkHODApproval(models.Model):
    id = models.BigAutoField(primary_key=True)
    # Track individual HOD approvals for Hotwork
    hotwork = models.ForeignKey(
        AddHotwork, on_delete=models.CASCADE, related_name="hod_approvals"
    )
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUserProfile, on_delete=models.SET_NULL, null=True, blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Engineer Officer (Department ID 2) checklist
    earthing_gts = models.CharField(max_length=10, blank=True, null=True)  # Yes/No

    # Electrical Officer (Department ID 3) checklist
    fire_sensor_ops = models.CharField(
        max_length=10,
        choices=OpsNonOpsChoices.choices,
        blank=True,
        null=True,
    )

    fire_sensor_non_ops_remarks = models.TextField(
        blank=True,
        null=True,
    )

    flood_sensor_ops = models.CharField(
        max_length=10,
        choices=OpsNonOpsChoices.choices,
        blank=True,
        null=True,
    )

    flood_sensor_non_ops_remarks = models.TextField(
        blank=True,
        null=True,
    )

    supply_point = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    iccp_off = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    # NBCDO Officer (Department ID 5) checklist
    fire_extinguisher = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    fire_hose = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    firemain_pressure = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    free_lagging = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    sentry_knowledge = models.CharField(
        max_length=3,
        choices=YesNoChoices.choices,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "Hotwork_hotworkhodapproval"
        unique_together = ("hotwork", "department")

    def __str__(self):
        return f"HOD Approval for {self.hotwork.hotwork_code} - {self.department.name}"


class HotworkProgressActivity(models.Model):
    """Track detailed progress activity history for hotwork"""

    id = models.BigAutoField(primary_key=True)

    hotwork = models.ForeignKey(
        AddHotwork, on_delete=models.CASCADE, related_name="progress_activities"
    )
    action = models.CharField(max_length=20, choices=ProgressAction)
    performed_by = models.ForeignKey(
        CustomUserProfile, on_delete=models.SET_NULL, null=True
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "Hotwork_hotworkprogressactivity"
        ordering = ("-performed_at",)

    def __str__(self):
        return f"{self.hotwork.hotwork_code} - {self.action} by {self.performed_by}"
