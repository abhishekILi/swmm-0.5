from django.db import models
from users.models import CustomUserProfile

from .managers import BaseManager


class WLMSEquipment(models.Model):
    objects = BaseManager()
    eqpt_id = models.IntegerField(blank=True, null=True)
    eqpt_name = models.CharField(max_length=255, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    control_cell_id = models.IntegerField(blank=True, null=True)
    sco_id = models.IntegerField(blank=True, null=True)
    depot_id = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="wed_equipment_created",
    )
    created_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="wed_equipment_updated",
    )
    updated_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return self.eqpt_name or ""

    class Meta:
        db_table = "WLMS_wlmsequipment"


class WLMSSpare(models.Model):
    objects = BaseManager()
    wlms_inventory = models.CharField(max_length=100, null=True, blank=True)
    item_code = models.CharField(max_length=100, null=True, blank=True)
    item_desc = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    eqpt = models.ForeignKey(
        WLMSEquipment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    denom_id = models.CharField(max_length=100, null=True, blank=True)
    sh_name = models.CharField(max_length=100, null=True, blank=True)
    latest_qty = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    typeofspare = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.item_code or ""

    class Meta:
        db_table = "WLMS_wlmsspare"


class SpareDataMap(models.Model):
    objects = BaseManager()
    equipment = models.ForeignKey(
        "sfd.ShipEquipment",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="wlms_spare_data_maps",
    )
    wed_equipment = models.ForeignKey(
        WLMSEquipment,
        on_delete=models.CASCADE,
        related_name="spare_data_maps",
        blank=True,
        null=True,
    )
    wed_spares = models.ForeignKey(
        WLMSSpare,
        on_delete=models.CASCADE,
        related_name="spare_data_maps",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.equipment} | {self.wed_equipment}"

    class Meta:
        db_table = "WLMS_sparedataMap"


class PlannedSparesDescription(models.Model):
    objects = BaseManager()
    wlms_spare_id = models.ForeignKey(WLMSSpare, on_delete=models.CASCADE, blank=True)
    routine_description_id = models.ForeignKey(
        "ems.RoutineDescription",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="wlms_planned_spares",
        db_column="routine_description_id",
    )
    spares_required = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        db_table = "WLMS_plannedsparesdescription"


class PlannedWEDSpareList(models.Model):
    objects = BaseManager()
    pattern_number = models.CharField(max_length=200, blank=True, default="")
    planned_spares_description = models.ForeignKey(
        PlannedSparesDescription,
        on_delete=models.CASCADE,
    )
    quantity_required = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pattern_number or self.pk)

    class Meta:
        db_table = "WLMS_plannedwedsparelist"


class DartWedSpare(models.Model):
    objects = BaseManager()
    issue_obj = models.ForeignKey(
        "obs.Issue",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    equipment_id = models.ForeignKey(
        "sfd.ShipEquipment",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="dart_wed_spares",
        db_column="equipment_id_id",
    )
    wed_spare = models.ForeignKey(
        WLMSSpare,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    dart_id = models.ForeignKey(
        "dart.InitiateDart",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="wed_spares",
        db_column="dart_id_id",
    )
    pattern = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True)
    modified_date = models.DateField(auto_now_add=True, blank=True, null=True)
    is_delete = models.BooleanField(default=False)

    def __str__(self):
        return str(self.description or self.pk)

    class Meta:
        db_table = "WLMS_dartwedspare"


class SurveyReceiptsDetails(models.Model):
    objects = BaseManager()
    user_id = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    wed_spares_id = models.ForeignKey(
        WLMSSpare,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    spare_cart_name = models.CharField(max_length=200, blank=True, default="")
    obs_spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    wed_routine_plan = models.ForeignKey(
        PlannedSparesDescription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    wed_dart = models.ForeignKey(
        DartWedSpare,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    is_save = models.BooleanField(default=False)
    is_survey = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_approval = models.BooleanField(default=False)
    wlms_status = models.CharField(max_length=200, blank=True, default="")
    sync_date = models.DateTimeField(auto_now=False, blank=True, null=True)
    wlms_survey_status = models.CharField(max_length=200, default="Pending")

    def __str__(self):
        return str(self.spare_cart_name or self.pk)

    class Meta:
        db_table = "WLMS_surveyreceiptsdetails"


class SurveyFormsDetails(models.Model):
    objects = BaseManager()
    survey_rec_id = models.ForeignKey(
        SurveyReceiptsDetails,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    rece_qty = models.CharField(max_length=200, blank=True, default="")
    held_certificate_type = models.CharField(max_length=200, blank=True, default="")
    held_certificate_no = models.CharField(max_length=200, blank=True, default="")
    held_certificate_date = models.DateField(null=True, blank=True)
    held_certificate = models.FileField(
        upload_to="wed_survey/",
        null=True,
        blank=True,
    )
    survey_no = models.CharField(max_length=200, blank=True, default="")
    wlms_survey_no = models.CharField(max_length=200, blank=True, default="")
    ss_remarks = models.CharField(max_length=200, blank=True, default="")
    created_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="wed_servey_created",
    )
    created_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="wed_servey_updated",
    )
    updated_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    scrap_qty = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return str(self.rece_qty or self.pk)

    class Meta:
        db_table = "WLMS_surveyformsdetails"


class SurveyFormsItems(models.Model):
    objects = BaseManager()
    survey_details_id = models.ForeignKey(
        SurveyFormsDetails,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    wed_spares_id = models.ForeignKey(
        WLMSSpare,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    item_serial_no = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "WLMS_surveyformsitems"


class PTSDemandDetails(models.Model):
    objects = BaseManager()
    user_id = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    wed_spares_id = models.ForeignKey(
        WLMSSpare,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    obs_spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    wed_routine_plan = models.ForeignKey(
        PlannedSparesDescription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    wed_dart = models.ForeignKey(
        DartWedSpare,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    survey_no = models.CharField(max_length=200, blank=True, default="")
    PTS_demand_no = models.CharField(max_length=200, blank=True, default="")
    demand_no = models.CharField(max_length=200, blank=True, default="")
    demand_qty = models.CharField(max_length=200, blank=True, default="")
    remarks = models.TextField(null=True, blank=True)
    is_save = models.BooleanField(default=False)
    is_pts = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    spare_cart_name = models.CharField(max_length=200, blank=True, default="")
    is_hod = models.BooleanField(default=False)
    is_approval = models.BooleanField(default=False)
    sync_date = models.DateTimeField(auto_now=False, blank=True, null=True)
    wlms_pts_status = models.CharField(max_length=200, default="Pending")
    wed_demandno = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = "WLMS_ptsdemanddetails"


class PTSItems(models.Model):
    objects = BaseManager()
    pts_details_id = models.ForeignKey(
        PTSDemandDetails,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    wed_spares_id = models.ForeignKey(
        WLMSSpare,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    item_serial_no = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return str(self.id)


class DemandDetails(models.Model):
    objects = BaseManager()
    user_id = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    wed_spares_id = models.ForeignKey(
        WLMSSpare,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    obs_spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    wed_routine_plan = models.ForeignKey(
        PlannedSparesDescription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    wed_dart = models.ForeignKey(
        DartWedSpare,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    survey_no = models.CharField(max_length=200, blank=True, default="")
    PTS_no = models.CharField(max_length=200, blank=True, default="")
    demand_no = models.CharField(max_length=200, blank=True, default="")
    demand_qty = models.CharField(max_length=200, blank=True, default="")
    remarks = models.TextField(null=True, blank=True)
    is_save = models.BooleanField(default=False)
    is_demand = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    sync_date = models.DateTimeField(auto_now=False, blank=True, null=True)
    is_rejected = models.BooleanField(default=False)
    spare_cart_name = models.CharField(max_length=200, blank=True, default="")
    demand_pdf = models.FileField(upload_to="wed_demand/", null=True, blank=True)
    is_hod = models.BooleanField(default=False)
    is_approval = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    wlms_demand_status = models.CharField(max_length=200, default="Pending")
    wed_demandno = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return str(self.survey_no or self.pk)

    class Meta:
        db_table = "WLMS_demanddetails"


class ReceiveDemandDetails(models.Model):
    objects = BaseManager()
    demand_details = models.ForeignKey(
        DemandDetails,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    pts_details = models.ForeignKey(
        PTSDemandDetails,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    demand_number = models.CharField(max_length=200, blank=True, null=True)
    demand_date = models.DateField(blank=True, null=True)
    demand_quantity = models.IntegerField(default=0)
    original_demand_qty = models.IntegerField(default=0, blank=True, null=True)
    demand_status = models.CharField(max_length=100, blank=True, null=True)
    swmm_demandno = models.CharField(max_length=200, blank=True, null=True)
    dart_no = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    gate_pass_no = models.CharField(max_length=200, blank=True, null=True)
    gate_pass_date = models.DateTimeField(auto_now=False, blank=True, null=True)
    received_qty = models.IntegerField(default=0, blank=True, null=True)
    received_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return str(self.demand_number)

    class Meta:
        db_table = "WLMS_receivedemanddetails"


class WEDIIF(models.Model):
    objects = BaseManager()
    user_id = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    is_sync = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_approval = models.BooleanField(default=False)
    sync_response = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)
    sync_date = models.DateTimeField(auto_now=False, blank=True, null=True)
    wlms_iif_status = models.CharField(max_length=200, default="Pending")

    def __str__(self):
        return str(self.pk)

    class Meta:
        db_table = "WLMS_wediif"


class WEDIIFDetails(models.Model):
    objects = BaseManager()
    wed_iif = models.ForeignKey(
        WEDIIF,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="details",
    )
    iif_no = models.CharField(max_length=200, blank=True, null=True)
    comly_in_other_eqpt = models.CharField(max_length=200, blank=True, null=True)
    annual_req = models.CharField(max_length=200, blank=True, null=True)
    phone_no = models.IntegerField(blank=True, null=True)
    Specification = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(null=True, blank=True)
    Qty_fitted_in_eqpt = models.CharField(max_length=200, blank=True, null=True)
    iif_photo = models.FileField(upload_to="wed_iif/", null=True, blank=True)
    proposed_MSL = models.CharField(max_length=200, blank=True, null=True)
    drawing_no = models.CharField(max_length=200, blank=True, null=True)
    drawing_doc = models.FileField(upload_to="wed_iif/", null=True, blank=True)
    poev_costing_rs = models.CharField(max_length=200, blank=True, null=True)
    bq_amount_rs = models.CharField(max_length=200, blank=True, null=True)
    bq_doc = models.FileField(upload_to="wed_iif/", null=True, blank=True)
    ss_remarks = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.iif_no or self.pk)

    class Meta:
        db_table = "WLMS_wediifdetails"


class SignalDemand(models.Model):
    objects = BaseManager()
    OPDEM = "OPDEM"
    STOREDEM = "STOREDEM"
    CANDEM = "CANDEM"

    DEMAND_TYPE_CHOICES = [
        (OPDEM, "Operational Demand"),
        (STOREDEM, "Store Demand"),
        (CANDEM, "Cannibalisation Demand"),
    ]

    REGISTERED = "REGISTERED"
    FORWARDED = "FORWARDED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (REGISTERED, "Registered"),
        (FORWARDED, "Forwarded"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
    ]

    demand_type = models.CharField(
        max_length=20,
        choices=DEMAND_TYPE_CHOICES,
    )
    demand_number = models.CharField(max_length=100)
    dtg = models.DateTimeField()
    requesting_ship = models.ForeignKey(
        "master.Ship",
        on_delete=models.PROTECT,
        related_name="raised_signal_demands",
        null=True,
    )
    receiver_ship = models.ForeignKey(
        "master.Ship",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="received_cannibalisation_demands",
    )
    equipment = models.ForeignKey(
        WLMSEquipment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="signal_demands",
    )
    wed_spare = models.ForeignKey(
        WLMSSpare,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="signal_demands",
    )
    obs_spare = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="wlms_signal_demands",
    )
    pts_number = models.CharField(max_length=100, blank=True, default="")
    demand_quantity = models.PositiveIntegerField(default=1)
    attachment = models.FileField(
        upload_to="wlms/signal_demands/",
        null=True,
        blank=True,
    )
    remarks = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=REGISTERED,
    )
    created_by = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        related_name="created_signal_demands",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "WLMS_signaldemand"
        ordering = ["-dtg", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=("demand_type", "demand_number"),
                name="unique_wlms_signal_demand_number",
            )
        ]

    def __str__(self):
        return f"{self.demand_type} - {self.demand_number}"
