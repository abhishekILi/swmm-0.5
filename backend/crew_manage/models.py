from django.conf import settings
from django.db import models
from django.utils import timezone

OnLeave = "On Leave"
TyDuty = "Ty Duty"
UserProfile = "users.CustomUserProfile"


class ActionChoices(models.TextChoices):
    PENDING = "Pending", "Pending"
    APPROVED = "Approved", "Approved"
    REJECTED = "Rejected", "Rejected"
    FORWARDED = "Forwarded", "Forwarded"
    RETURNED = "Returned", "Returned"


class AddressDetails(models.Model):
    # Primary key (auto-increment)
    id = models.BigAutoField(primary_key=True)

    # Permanent Address
    address_permanent = models.TextField(blank=True, null=True)
    country_permanent = models.CharField(max_length=100, blank=True, null=True)
    email_permanent = models.EmailField(blank=True, null=True)
    number_permanent = models.CharField(max_length=20, blank=True, null=True)

    # Other Address
    line1_other = models.CharField(max_length=255, blank=True, null=True)
    line2_other = models.CharField(max_length=255, blank=True, null=True)
    district_other = models.CharField(max_length=100, blank=True, null=True)
    city_other = models.CharField(max_length=100, blank=True, null=True)
    state_other = models.CharField(max_length=100, blank=True, null=True)
    country_other = models.CharField(max_length=100, blank=True, null=True)
    pincode_other = models.CharField(max_length=20, blank=True, null=True)
    email_other = models.EmailField(blank=True, null=True)
    contact_other = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_addressdetails"

    def __str__(self):
        return f"AddressDetails {self.id}"


class LeaveDetails(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField()
    type_of_leave = models.CharField(max_length=100)
    category_of_leave = models.CharField(max_length=100)
    commencement_date = models.DateField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    no_of_days = models.PositiveIntegerField()
    leave_year = models.CharField(max_length=4, blank=True, null=True)
    prefix_date = models.DateField(blank=True, null=True)
    prefix_days = models.PositiveIntegerField(default=0)
    suffix_date = models.DateField(blank=True, null=True)
    suffix_days = models.PositiveIntegerField(default=0)
    leave_station = models.TextField(blank=True, null=True)
    travel_start_date = models.DateField(blank=True, null=True)
    tt_days = models.PositiveIntegerField(blank=True, null=True)
    station_type = models.CharField(max_length=10, blank=True, null=True)  # "In"/"Out"
    railway_station = models.CharField(max_length=100, blank=True, null=True)
    lmc_date = models.DateField(blank=True, null=True)
    medical_category = models.CharField(max_length=100, blank=True, null=True)
    with_without_passage = models.CharField(max_length=20, blank=True, null=True)
    passage_type = models.CharField(max_length=50, blank=True, null=True)
    ration_type = models.CharField(max_length=50, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    address_id = models.ForeignKey(
        AddressDetails, on_delete=models.CASCADE, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected"),
            ("Returned", "Returned"),
        ],
        default="Pending",
    )

    class Meta:
        db_table = "crewmanage_leavedetails"

    def __str__(self):
        return f"Leave {self.id} - User {self.user_id} ({self.status})"


class LeaveApprovalWorkflow(models.Model):
    id = models.BigAutoField(primary_key=True)
    leave_id = models.ForeignKey(
        LeaveDetails, on_delete=models.CASCADE, related_name="approval_workflow"
    )

    reg = models.CharField(max_length=100, null=True, blank=True)
    reg_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    do = models.CharField(max_length=100, null=True, blank=True)
    do_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    dhod = models.CharField(max_length=100, null=True, blank=True)
    dhod_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    hod = models.CharField(max_length=100, null=True, blank=True)
    hod_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    co = models.CharField(max_length=100, null=True, blank=True)
    co_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    gx = models.CharField(max_length=100, null=True, blank=True)
    gx_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )
    comment = models.TextField(blank=True, null=True)
    return_remarks = models.TextField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_leave_approval_workflow"

    def __str__(self):
        return str(self.reg or self.pk)


class LeaveApprovalHistory(models.Model):
    APPROVAL_LEVEL_CHOICES = (
        ("USER", "User"),
        ("REG", "Registrar"),
        ("DO", "District Officer"),
        ("DHOD", "Deputy Head of Department"),
        ("HOD", "Head of Department"),
        ("CO", "Controlling Officer"),
        ("GX", "Government Executive"),
    )

    id = models.BigAutoField(primary_key=True)
    leave_id = models.ForeignKey(
        LeaveDetails, on_delete=models.CASCADE, related_name="approval_history"
    )

    approved_by_id = models.IntegerField()
    action_taken = models.CharField(max_length=20, choices=ActionChoices)
    action_datetime = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "crewmanage_leave_approval_history"
        ordering = ("-action_datetime",)

    @classmethod
    def log_action(
        cls, leave_id, user_id, user_name, action, level, remarks=None, ip=None
    ):
        """
        Log every action in the history table.
        NOTE: Does not overwrite workflow table except for initial 'Submitted'.
        """
        history = cls.objects.create(
            leave_id=leave_id,
            approved_by_id=user_id,
            action_taken=action,
            ip_address=ip,
        )

        # Only create initial pending state for first submission
        if action == "Submitted":
            workflow, _ = LeaveApprovalWorkflow.objects.get_or_create(leave_id=leave_id)
            setattr(workflow, level.lower(), str(user_id))
            setattr(workflow, f"{level.lower()}_action", "Pending")
            workflow.save()

        return history

    def __str__(self):
        return str(self.action_taken or self.pk)


class TypeOfTempDuty(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_typeoftempduty"

    def __str__(self):
        return self.name


class ModeOfTravel(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_modeoftravel"

    def __str__(self):
        return self.name


class RationType(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_rationtype"

    def __str__(self):
        return self.name


class PassageType(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    def __str__(self):
        return self.name


class PlaceOfTyDuty(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_placeoftyduty"

    def __str__(self):
        return self.name


class TypeOfLeave(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()
    leave_numbers = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "crewmanage_typeofleave"

    def __str__(self):
        return self.name


class Railway(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_railway"

    def __str__(self):
        return self.name


class MedicalCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_medicalcategory"

    def __str__(self):
        return self.name


class LtcDays(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField()

    class Meta:
        db_table = "crewmanage_ltcdays"

    def __str__(self):
        return self.name


class TemporaryDuty(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField()
    temp_duty_type = models.CharField(max_length=100)
    commencement_date = models.DateField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    no_of_days = models.PositiveIntegerField()
    tt_days = models.PositiveIntegerField(blank=True, null=True)
    joining_days = models.PositiveIntegerField(blank=True, null=True)
    station_type = models.CharField(max_length=10, blank=True, null=True)  # "In"/"Out"
    gx_unit = models.CharField(max_length=100, blank=True, null=True)
    place_of_duty = models.CharField(max_length=255, blank=True, null=True)
    with_without_passage = models.CharField(max_length=20, blank=True, null=True)
    passage_type = models.CharField(max_length=50, blank=True, null=True)
    ration_type = models.CharField(max_length=50, blank=True, null=True)
    authority_number = models.CharField(max_length=100, blank=True, null=True)
    authority_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    file_upload = models.FileField(upload_to="ty_duty_files/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    address_id = models.ForeignKey(
        AddressDetails, on_delete=models.CASCADE, null=True, blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected"),
            ("Returned", "Returned"),
        ],
        default="Pending",
    )

    class Meta:
        db_table = "crewmanage_temporaryduty"

    def __str__(self):
        return f"TY Duty {self.id} - User {self.user_id} ({self.status})"


class TemporaryDutyApprovalWorkflow(models.Model):
    id = models.BigAutoField(primary_key=True)
    duty = models.ForeignKey(
        TemporaryDuty, on_delete=models.CASCADE, related_name="approval_workflow"
    )

    reg = models.CharField(max_length=100, null=True, blank=True)
    reg_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    do = models.CharField(max_length=100, null=True, blank=True)
    do_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    dhod = models.CharField(max_length=100, null=True, blank=True)
    dhod_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    hod = models.CharField(max_length=100, null=True, blank=True)
    hod_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    co = models.CharField(max_length=100, null=True, blank=True)
    co_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    gx = models.CharField(max_length=100, null=True, blank=True)
    gx_action = models.CharField(
        max_length=20, choices=ActionChoices, null=True, blank=True
    )

    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True, null=True)
    return_remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "ty_duty_approval_workflow"

    def __str__(self):
        return str(self.reg or self.pk)


class TemporaryDutyApprovalHistory(models.Model):
    APPROVAL_LEVEL_CHOICES = (
        ("USER", "User"),
        ("REG", "Registrar"),
        ("DO", "District Officer"),
        ("DHOD", "Deputy Head of Department"),
        ("HOD", "Head of Department"),
        ("CO", "Controlling Officer"),
        ("GX", "Government Executive"),
    )

    id = models.BigAutoField(primary_key=True)
    duty = models.ForeignKey(
        TemporaryDuty, on_delete=models.CASCADE, related_name="approval_history"
    )
    user_id = models.IntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    action = models.CharField(max_length=20, choices=ActionChoices)
    level = models.CharField(
        max_length=10, choices=APPROVAL_LEVEL_CHOICES, blank=True, null=True
    )
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "crewmanage_temporarydutyapprovalhistory"

    @classmethod
    def log_action(cls, duty, user_id, user_name, action, level=None, remarks=None):
        cls.objects.create(
            duty=duty,
            user_id=user_id,
            user_name=user_name,
            action=action,
            level=level,
            remarks=remarks,
        )

    def __str__(self):
        return str(self.user_name or self.pk)


class GXForm(models.Model):
    id = models.BigAutoField(primary_key=True)
    gx_no = models.CharField(max_length=50)
    gx_date = models.DateTimeField()
    occurrence = models.CharField(max_length=2, choices=[("AM", "AM"), ("PM", "PM")])
    pdf_file = models.FileField(upload_to="gx_forms/", blank=True, null=True)
    leave_id = models.CharField(max_length=50, null=True)

    class Meta:
        db_table = "crewmanage_gxform"

    def __str__(self):
        return str(self.gx_no or self.pk)


ON_LEAVE = "On Leave"

TY_DUTY = "Ty Duty"


class LeaveApplication(models.Model):
    """
    Unified Leave / TY-Duty application.
    Submitted by any personnel; HOD/DY-HOD/CO can approve or reject.
    Applications submitted *by* HOD/DY-HOD/CO are auto-approved.
    """

    LEAVE_TYPE_CHOICES = (
        (OnLeave, OnLeave),
        (TyDuty, TyDuty),
    )

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    )
    id = models.BigAutoField(primary_key=True)

    # ── Personnel snapshot ────────────────────────────────────────────────────
    personal_number = models.CharField(max_length=50)
    rank = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)

    # ── Type ──────────────────────────────────────────────────────────────────
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)

    # ── Prefix (shared by both Leave & TY Duty) ───────────────────────────────
    has_prefix = models.BooleanField(default=False)
    prefix_start_date = models.DateField(null=True, blank=True)
    # TY-Duty only
    prefix_start_time = models.TimeField(null=True, blank=True)

    # ── Core dates ────────────────────────────────────────────────────────────
    start_date = models.DateField()  # Commencement date
    end_date = models.DateField()  # Completion date

    # ── Suffix ────────────────────────────────────────────────────────────────
    suffix_completion_date = models.DateField(null=True, blank=True)
    # TY-Duty only
    suffix_completion_time = models.TimeField(null=True, blank=True)

    # ── Reporting (TY-Duty: same as suffix completion time; Leave: date only) ─
    reporting_date = models.DateField(null=True, blank=True)
    reporting_time = models.TimeField(null=True, blank=True)  # TY-Duty only

    # ── Calculated ────────────────────────────────────────────────────────────
    no_of_days = models.PositiveIntegerField(default=0)

    # ── Station / reason ─────────────────────────────────────────────────────
    # "Leave Station" for Leave; "TY Duty Station" for TY Duty
    station = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    remark = models.TextField(blank=True)

    # ── Attachment ────────────────────────────────────────────────────────────
    attachment = models.FileField(upload_to="leave_attachments/", null=True, blank=True)

    # ── Workflow ──────────────────────────────────────────────────────────────
    application_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pending"
    )
    rejection_reason = models.TextField(blank=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    applied_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        related_name="leave_applications_submitted",
    )
    approved_rejected_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_applications_actioned",
    )
    approved_rejected_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_leaveapplication"
        ordering = ("-applied_at",)
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"

    # ─────────────────────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        """Auto-compute no_of_days = end_date - start_date + 1."""
        if self.start_date and self.end_date:
            delta = (self.end_date - self.start_date).days + 1
            self.no_of_days = max(delta, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.name} ({self.personal_number}) — "
            f"{self.leave_type} | {self.start_date} → {self.end_date} [{self.application_status}]"
        )


# ─────────────────────────────────────────────────────────────────────────
class PersonnelStatusLog(models.Model):
    id = models.AutoField(primary_key=True)
    rank = models.CharField(max_length=50, null=True)
    name = models.CharField(max_length=50, null=True)
    personnel_number = models.CharField(max_length=50, null=True)
    department = models.CharField(max_length=50, null=True)
    designation = models.CharField(max_length=50, null=True)
    status = models.CharField(max_length=50)
    log_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    leave_application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="status_logs",
    )

    def __str__(self):
        return f"Personnel {self.personnel_number} - {self.status} on {self.log_date}"


"""
models.py — Watch Station Bill (WS Bill) Module
apps/watchbill/models.py

Run after adding to INSTALLED_APPS:
    python manage.py makemigrations watchbill
    python manage.py migrate
"""


class CivilianOfficial(models.Model):
    ROLE_CHOICES = (
        ("Barber", "Barber"),
        ("CIV Bearer", "CIV Bearer"),
        ("MES Boy", "MES Boy"),
        ("Canteen Manager", "Canteen Manager"),
        ("NAAFI Staff", "NAAFI Staff"),
        ("Dhobi", "Dhobi"),
        ("Cook (Civ)", "Cook (Civ)"),
        ("Other", "Other"),
    )
    id = models.BigAutoField(primary_key=True)
    name_snapshot = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    ref_id = models.CharField(max_length=50, blank=True, help_text="Aadhar / Emp No.")
    contact = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    person_type = models.CharField(max_length=50, blank=True)
    rank_snapshot = models.CharField(max_length=80, blank=True)
    pno_snapshot = models.CharField(max_length=50, blank=True)
    dept_snapshot = models.CharField(max_length=100, blank=True)
    desig_snapshot = models.CharField(max_length=150, blank=True)
    service_no = models.CharField(max_length=100, blank=True)
    fleet = models.CharField(max_length=200, blank=True)
    ship = models.CharField(max_length=200, blank=True)
    cid = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_civilianofficial"
        verbose_name = "Civilian Official"
        verbose_name_plural = "Civilian Officials"
        ordering = (
            "role",
            "name_snapshot",
        )

    def __str__(self):
        return f"{self.name_snapshot} ({self.role})"


class Sailing(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("completed", "Completed"),
    )
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=200)
    area = models.CharField(max_length=200, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    co_name = models.CharField(
        max_length=150, blank=True, verbose_name="Commanding Officer"
    )
    xo_name = models.CharField(
        max_length=150, blank=True, verbose_name="Executive Officer"
    )
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    completed_at = models.DateField(null=True, blank=True)
    civilians = models.ManyToManyField(
        CivilianOfficial, blank=True, related_name="sailings"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_sailing"
        verbose_name = "Sailing"
        verbose_name_plural = "Sailings"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} ({self.start_date})"


class SailingPersonnel(models.Model):
    STATUS_CHOICES = (
        ("Present", "Present"),
        (OnLeave, OnLeave),
        (TyDuty, TyDuty),
    )
    id = models.BigAutoField(primary_key=True)

    sailing = models.ForeignKey(
        Sailing, on_delete=models.CASCADE, related_name="personnel"
    )

    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sailing_entries",
    )

    # Existing snapshot fields
    rank_snapshot = models.CharField(max_length=80, blank=True)
    name_snapshot = models.CharField(max_length=200)
    pno_snapshot = models.CharField(max_length=50)
    dept_snapshot = models.CharField(max_length=100, blank=True)
    desig_snapshot = models.CharField(max_length=150, blank=True)

    # Civilian / embarked person details
    person_type = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=150, blank=True)
    service_no = models.CharField(max_length=100, blank=True)
    fleet = models.CharField(max_length=200, blank=True)
    ship = models.CharField(max_length=200, blank=True)
    cid = models.CharField(max_length=100, blank=True)
    contact = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    # Editable fields
    watch_station = models.CharField(max_length=150, blank=True)
    action_station = models.CharField(max_length=150, blank=True)
    status_override = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Present"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sailing_personnel",
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "crewmanage_sailingpersonnel"
        verbose_name = "Sailing Personnel"
        verbose_name_plural = "Sailing Personnel"
        unique_together = ("sailing", "pno_snapshot")
        ordering = ("dept_snapshot", "rank_snapshot")

    def __str__(self):
        return f"{self.name_snapshot} — {self.sailing.name}"


class PersonnelAssignment(models.Model):
    """
    Stores W&S Bill assignment fields per personnel per sailing.
    One record per (sailing, pno) — upserted on save.
    """

    id = models.BigAutoField(primary_key=True)

    sailing = models.ForeignKey(
        Sailing, on_delete=models.CASCADE, related_name="assignments"
    )
    pno = models.CharField(max_length=50, db_index=True)
    name_snapshot = models.CharField(max_length=200, blank=True)
    rank_snapshot = models.CharField(max_length=80, blank=True)
    dept_snapshot = models.CharField(max_length=100, blank=True)

    # Editable assignment columns
    w3 = models.CharField(max_length=50, blank=True)
    w2 = models.CharField(max_length=50, blank=True)
    action = models.CharField(max_length=100, blank=True)
    defence = models.CharField(max_length=100, blank=True)
    cruising = models.CharField(max_length=100, blank=True)
    shelter = models.CharField(max_length=100, blank=True)
    emergency = models.CharField(max_length=100, blank=True)
    lr = models.CharField(max_length=50, blank=True)
    mess = models.CharField(max_length=50, blank=True)
    ssd = models.CharField(max_length=50, blank=True)
    mess_stn = models.CharField(max_length=50, blank=True)
    section = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    BLOOD_GROUP_CHOICES = (
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
    )

    blood_group = models.CharField(
        max_length=5, blank=True, choices=BLOOD_GROUP_CHOICES
    )

    class Meta:
        db_table = "crewmanage_personnelassignment"
        unique_together = ("sailing", "pno")
        verbose_name = "Personnel Assignment"
        verbose_name_plural = "Personnel Assignments"
        ordering = ("dept_snapshot", "rank_snapshot")

    def __str__(self):
        return f"{self.name_snapshot} ({self.pno}) — {self.sailing.name}"


class ActionStationMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_actionstationmaster"
        ordering = ("name",)
        verbose_name = "Action Station (Master)"
        verbose_name_plural = "Action Stations (Master)"

    def __str__(self):
        return self.name


class DefenceStationMaster(models.Model):
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_defencestationmaster"
        ordering = ("name",)
        verbose_name = "Defence Station (Master)"
        verbose_name_plural = "Defence Stations (Master)"

    def __str__(self):
        return self.name


class CruisingStationMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_cruisingstationmaster"
        ordering = ("name",)
        verbose_name = "Cruising Station (Master)"
        verbose_name_plural = "Cruising Stations (Master)"

    def __str__(self):
        return self.name


class ShelterStationMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Shelter Station (Master)"
        verbose_name_plural = "Shelter Stations (Master)"

    def __str__(self):
        return self.name


class EmergencyStationMaster(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_emergencystationmaster"
        ordering = ("name",)
        verbose_name = "Emergency Station (Master)"
        verbose_name_plural = "Emergency Stations (Master)"

    def __str__(self):
        return self.name


class SailorRankClassification(models.Model):
    """
    Reference-only master: classifies a rank name as Senior or Junior Sailor.
    Not linked to any other model/table — purely a lookup list per the spec.
    """

    CLASS_CHOICES = (("Senior", "Senior"), ("Junior", "Junior"))
    id = models.BigAutoField(primary_key=True)
    rank_name = models.CharField(max_length=100, unique=True)
    classification = models.CharField(
        max_length=10, choices=CLASS_CHOICES, default="Junior"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "crewmanage_sailorrankclassification"
        ordering = ("rank_name",)
        verbose_name = "Junior/Senior Sailor Classification"
        verbose_name_plural = "Junior/Senior Sailor Classifications"

    def __str__(self):
        return f"{self.rank_name} — {self.classification}"
