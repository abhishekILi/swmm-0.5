from django.utils import timezone
from drf_spectacular.utils import extend_schema_serializer
from master.models import (
    ChMasterShipRemarksBy,
    ChMasterSymptoms,
    MRequiredAssistance,
    MSeverity,
    RefitMaintenancePeriod,
)
from obs.models import Denomination
from rest_framework import serializers
from sfd.models import Equipment

from .models import CompleteDefectDart, InitiateDart, InitiateRADL, RADLMaster

OPERATION_STATUS = "Operation status, e.g. success or error"

SUCCESS_ERROR = "Success or error message"

DATE_FORMAT = "%d-%b-%Y"


class RADLMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = RADLMaster
        fields = "__all__"


class GeneratedDLIIReportSerializer(serializers.ModelSerializer):
    rows_count = serializers.IntegerField(source="total_dl_rows")
    refit = serializers.CharField(source="refit_type_name", allow_null=True)

    class Meta:
        model = RADLMaster
        fields = [
            "id",
            "ra_dl_name",
            "dockyard_name",
            "refit",
            "rows_count",
            "created_date",
        ]


class GeneratedDLIIReportRowSerializer(serializers.ModelSerializer):
    ra_dl_name = serializers.CharField(source="dl_key", allow_blank=True)
    eq_name = serializers.SerializerMethodField()
    description = serializers.CharField(
        source="initiate_dart.defective_discriptions", allow_blank=True
    )
    defective_component = serializers.CharField(
        source="initiate_dart.defective_component", allow_blank=True
    )

    class Meta:
        model = InitiateRADL
        fields = [
            "id",
            "dl_no",
            "ra_dl_name",
            "dl_type",
            "status",
            "eq_name",
            "description",
            "defective_component",
        ]

    def get_eq_name(self, obj):
        equipment_ship = getattr(obj.initiate_dart, "equipment_ship", None)
        return getattr(equipment_ship, "nomenclature", None) or "-"


class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChMasterSymptoms
        fields = ["id", "symptom_code"]


class SeveritySerializer(serializers.ModelSerializer):
    class Meta:
        model = MSeverity
        fields = ["id", "severity_code", "severity_name"]


class ShipRemarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChMasterShipRemarksBy
        fields = ["id", "description"]


@extend_schema_serializer(component_name="DartEquipment")
class EquipmentSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source="equipment_class", read_only=True)
    equipment_code = serializers.CharField(read_only=True)
    equipment_model = serializers.CharField(source="model", read_only=True)

    class Meta:
        model = Equipment
        fields = [
            "id",
            "equipment_name",
            "equipment_code",
            "equipment_model",
        ]


class RefitMaintenancePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefitMaintenancePeriod
        fields = ["id", "name", "occasion"]


class MaintenancePeriodDetailSerializer(serializers.ModelSerializer):
    maintaince_period_type = serializers.CharField(source="maintenance_period")
    occassion = serializers.CharField(source="occasion")
    period_name = serializers.CharField(source="name")
    start_date = serializers.DateField(source="actual_start_date")
    end_date = serializers.DateField(source="actual_end_date")

    class Meta:
        model = RefitMaintenancePeriod
        fields = [
            "id",
            "maintaince_period_type",
            "occassion",
            "period_name",
            "start_date",
            "end_date",
        ]


class RefitOperationalOccasionPeriodSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="occasion")

    class Meta:
        model = RefitMaintenancePeriod
        fields = [
            "id",
            "name",
            "type",
            "maintenance_period",
            "actual_start_date",
            "actual_end_date",
        ]


class RefitOperationalOccasionResponseSerializer(serializers.Serializer):
    title = serializers.CharField()
    pqr = serializers.CharField()
    ref = serializers.CharField()
    refit_periods = RefitOperationalOccasionPeriodSerializer(many=True)
    maint_periods = RefitOperationalOccasionPeriodSerializer(many=True)


class GetMaintenancePeriodTypeResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = serializers.ListField(child=serializers.CharField())


class GetMaintenancePeriodOccasionResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = serializers.ListField(child=serializers.CharField())


class GetMaintenancePeriodNameItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    end_date = serializers.DateField(allow_null=True)


class GetMaintenancePeriodNameResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = GetMaintenancePeriodNameItemSerializer(many=True)


class AssistanceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="required_assistance_id", read_only=True)

    class Meta:
        model = MRequiredAssistance
        fields = [
            "id",
            "required_assistance_for",
            "required_assistance_code",
        ]


class AddDartMetadataSerializer(serializers.Serializer):
    # New clean & professional snake_case/standard fields
    equipment_list = EquipmentSerializer(many=True, source="ec_code")
    spares_list = serializers.ListField(
        child=serializers.DictField(), source="spare_obj"
    )
    previous_dart_no = serializers.CharField(
        allow_null=True, required=False, source="last_serial"
    )
    next_suggested_dart_no = serializers.CharField(
        allow_null=True, required=False, source="new_serial"
    )
    ilms_objs = serializers.ListField(child=serializers.DictField())
    maintenance_periods = MaintenancePeriodDetailSerializer(many=True, required=False)
    refit_period = MaintenancePeriodDetailSerializer(many=True, required=False)
    ops_period = MaintenancePeriodDetailSerializer(many=True, required=False)
    symptoms = SymptomSerializer(many=True, source="symptom_list")
    severities = SeveritySerializer(many=True, source="severity_list")
    remarks_by_list = ShipRemarkSerializer(many=True, source="remark_list")
    assistance_options = AssistanceSerializer(many=True, source="assistance_list")
    oem_pil_spares_list = serializers.ListField(
        child=serializers.DictField(), source="oem_pil_spares"
    )
    denominations = serializers.ListField(child=serializers.DictField())
    trial_agencies = serializers.ListField(
        child=serializers.DictField(), source="trial_agency", required=False
    )
    maitainance_period_types = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    maitianance_period_occasions = serializers.DictField(required=False)


# ──────────────────────────────────────────────────────────────
# Complete Defect Dart Serializer
# ──────────────────────────────────────────────────────────────


class CompleteDefectDartSerializer(serializers.ModelSerializer):
    # Read-only display names
    repair_agency_name = serializers.StringRelatedField(
        source="repair_agency_code", read_only=True
    )
    diagnostic_name = serializers.StringRelatedField(
        source="diagnostic_code", read_only=True
    )
    repair_name = serializers.StringRelatedField(source="repair_code", read_only=True)
    delay_name = serializers.StringRelatedField(source="delay_code", read_only=True)

    class Meta:
        model = CompleteDefectDart
        fields = "__all__"


# ──────────────────────────────────────────────────────────────
# Complete Dart List Serializer (InitiateDart + completion data)
# ──────────────────────────────────────────────────────────────


class CompleteDartListSerializer(serializers.ModelSerializer):
    """Serializer for complete_dart_list endpoint — closed DARTs with completion details"""

    # Nested completion records
    complete_defect_dart_set = CompleteDefectDartSerializer(many=True, read_only=True)

    # Read-only display names for FK fields
    symptom_code_name = serializers.StringRelatedField(
        source="symptom_code", read_only=True
    )
    serverity_code_name = serializers.StringRelatedField(
        source="severity_code", read_only=True
    )
    remark_code_name = serializers.StringRelatedField(
        source="remark_code", read_only=True
    )
    department_name = serializers.StringRelatedField(
        source="department_id", read_only=True
    )
    equipment_ship_name = serializers.CharField(
        source="equipment_ship.nomenclature", read_only=True, default=None
    )
    equipment_ems_name = serializers.CharField(
        source="equipment_ems.name", read_only=True, default=None
    )

    class Meta:
        model = InitiateDart
        fields = "__all__"


class PendingDefectSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    nomenclature = serializers.CharField(
        source="equipment_ship.nomenclature", read_only=True, default=""
    )
    sub_dept = serializers.CharField(
        source="equipment_ship.sub_department_f_key.name", read_only=True, default=""
    )
    eq_name = serializers.CharField(
        source="equipment_ship.equipment.equipment_class", read_only=True, default=""
    )
    occasion = serializers.CharField(source="dart_occasion", read_only=True, default="")
    remarks = serializers.SerializerMethodField()
    opra_no = serializers.SerializerMethodField()
    dl_no = serializers.SerializerMethodField()
    is_gd = serializers.BooleanField(
        source="is_guarantee_defect", read_only=True, default=False
    )
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = InitiateDart
        fields = [
            "id",
            "dart_number",
            "dart_date",
            "rectification_date",
            "status",
            "nomenclature",
            "defective_discriptions",
            "sub_dept",
            "eq_name",
            "occasion",
            "maintenance_period",
            "remarks",
            "opra_no",
            "dl_no",
            "cmms_sync_status",
            "is_gd",
            "is_overdue",
        ]

    def get_status(self, obj) -> str:
        return "Closed" if obj.is_closed else "Open"

    def get_remarks(self, obj) -> str:
        return obj.remark_code.description if obj.remark_code else "-"

    def get_opra_no(self, obj) -> str | InitiateRADL:
        try:
            ra_record = (
                InitiateRADL.objects.filter(initiate_dart=obj, dl_type="RA")
                .order_by("-id")
                .first()
            )
            if ra_record:
                return ra_record.dl_key or ""
        except Exception:
            pass
        return ""

    def get_dl_no(self, obj) -> str | InitiateRADL:
        try:
            dl_record = (
                InitiateRADL.objects.filter(
                    initiate_dart=obj, dl_type__in=["DL", "DL-II", "DL-III"]
                )
                .order_by("-id")
                .first()
            )
            if dl_record:
                return dl_record.dl_key or ""
        except Exception:
            pass
        return ""

    def get_is_overdue(self, obj) -> bool:
        if not obj.is_closed and obj.rectification_date:
            return obj.rectification_date < timezone.now().date()
        return False


class DepartmentShortSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class PendingDefectFilterOptionsSerializer(serializers.Serializer):
    sub_departments = serializers.ListField(child=serializers.CharField())
    maintenance_periods = serializers.ListField(child=serializers.CharField())
    dart_occasions = serializers.ListField(child=serializers.CharField())
    equipment_nomenclatures = serializers.ListField(child=serializers.CharField())
    equipment_names = serializers.ListField(child=serializers.CharField())
    min_date = serializers.CharField(allow_null=True)
    max_date = serializers.CharField(allow_null=True)


class PendingDefectsResponseSerializer(serializers.Serializer):
    is_privileged = serializers.BooleanField()
    all_departments = DepartmentShortSerializer(many=True)
    selected_dept_id = serializers.IntegerField(allow_null=True)
    filter_options = PendingDefectFilterOptionsSerializer()
    open_defects = PendingDefectSerializer(many=True)
    dl_3_defects = PendingDefectSerializer(many=True)


# ──────────────────────────────────────────────────────────────
# DART Dashboard Serializers
# ──────────────────────────────────────────────────────────────


class SubDeptStatusSerializer(serializers.Serializer):
    """Sub-department operational status tile data"""

    name = serializers.CharField()
    status = serializers.CharField()  # "Ops" or "Non-Ops"
    count = serializers.IntegerField()


class SubDeptEquipmentSerializer(serializers.Serializer):
    """Sub-department equipment gauge data"""

    sub_dept = serializers.CharField()
    operational = serializers.IntegerField()
    non_operational = serializers.IntegerField()
    total = serializers.IntegerField()


class MonthlyChartEntrySerializer(serializers.Serializer):
    """Dynamic keys per sub-department + month + total"""

    month = serializers.CharField()
    total = serializers.IntegerField(default=0)

    # Sub-department counts are dynamic keys — handled via to_representation
    def to_representation(self, instance):
        # instance is a dict like {"month": "Jan 2026", "Hull": 3, "Elec": 1, "total": 4}
        return instance


class MaintenancePeriodSerializer(serializers.Serializer):
    """Maintenance period timeline entry"""

    maintenance_period = serializers.CharField()
    occasion = serializers.CharField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    is_current = serializers.BooleanField()


class ShipStatusSerializer(serializers.Serializer):
    """Ship status nested serializer"""

    status = serializers.CharField()
    refit_name = serializers.CharField(allow_null=True, required=False)
    start_date = serializers.CharField(allow_null=True, required=False)
    end_date = serializers.CharField(allow_null=True, required=False)


class DartDashboardSerializer(serializers.Serializer):
    """Top-level serializer for the entire DART Dashboard response"""

    ship_status = ShipStatusSerializer(allow_null=True)
    open_darts_ops_count = serializers.IntegerField()
    open_darts_refit_count = serializers.IntegerField()
    due_for_closing_count = serializers.IntegerField()
    sub_dept_status_data = SubDeptStatusSerializer(many=True)
    sub_dept_equipment_data = SubDeptEquipmentSerializer(many=True)
    open_chart_data = MonthlyChartEntrySerializer(many=True)
    closed_chart_data = MonthlyChartEntrySerializer(many=True)
    sub_depts = serializers.ListField(child=serializers.CharField())
    maintenance_periods = MaintenancePeriodSerializer(many=True)


class EmptyStringImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Swagger often sends "string" or "" for empty file fields in JSON mode
        if isinstance(data, str):
            return None
        return super().to_internal_value(data)


class EmptyStringFileField(serializers.FileField):
    def to_internal_value(self, data):
        # Swagger or frontend sends "string" or "" for empty file fields
        if isinstance(data, str):
            return None
        return super().to_internal_value(data)


class EmptyStringIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if data == "" or data is None or data == "null" or data == "undefined":
            return None
        try:
            return super().to_internal_value(data)
        except Exception:
            return None


class EmptyStringDateField(serializers.DateField):
    def to_internal_value(self, data):
        if data == "" or data is None or data == "null" or data == "undefined":
            return None
        return super().to_internal_value(data)


class FlexibleCharField(serializers.CharField):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = (
                data.get("value")
                or data.get("id")
                or data.get("pk")
                or data.get("code")
                or ""
            )
        if data is None or data == "null" or data == "undefined":
            return ""
        return super().to_internal_value(str(data))


class FlexibleIntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = (
                data.get("value")
                or data.get("id")
                or data.get("pk")
                or data.get("code")
            )
        if data == "" or data is None or data == "null" or data == "undefined":
            return None
        try:
            return int(data)
        except Exception:
            return None


class InitiateDartSerializer(serializers.Serializer):
    """
    Matches the legacy HTML form (new_add_dart.html) field names exactly.
    Content-Type: multipart/form-data (because of file upload).

    Fields are grouped by the 3 form types:
      - Common (all types)
      - Defect specific
      - Guarantee Defect specific
      - ASR / A's & A's / ABER specific
    """

    # ── dart_type (radio: "Defect" | "Guarantee Defect" | "ASR") ────────────
    dart_type = serializers.CharField(
        required=True,
        help_text='Form type: "Defect", "Guarantee Defect", or "ASR"',
    )

    # ── Equipment (select dropdown → sends ShipEquipment.id as string) ──────
    # Only one of these is sent depending on dart_type
    nomenclature = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="ShipEquipment ID — for Defect type",
    )
    g_nomenclature = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="ShipEquipment ID — for Guarantee Defect type",
    )
    a_nomenclature = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="ShipEquipment ID — for ASR type",
    )

    # ── COMMON: Dropdowns (select → sends DB record ID as string) ───────────
    symptoms = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="ChMasterSymptoms.id",
    )
    severity = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="MSeverity.id",
    )
    ssRemarks = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="ChMasterShipRemarksBy.id",
    )
    requiredAssistance = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="MRequiredAssistance.required_assistance_id",
    )

    # ── COMMON: Maintenance period & occasion (modal selects) ───────────────
    maintenance_period = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='"OPERATIONAL" or "REFIT"',
    )
    dart_occasion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Occasion name, e.g. "Normal Defect", "DL II", etc.',
    )
    ops_period_id = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="RefitMaintenancePeriod.id — for refit/ops link",
    )

    # ── DEFECT: Dates (flatpickr → "YYYY-MM-DD" string) ────────────────────
    defectDate = EmptyStringDateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "iso-8601"],
    )
    scheduledDate = EmptyStringDateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "iso-8601"],
        help_text="Tentative Defect Resolution date",
    )

    # ── DEFECT: Text inputs ─────────────────────────────────────────────────
    defect_description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Defect Description text (Primary)",
    )
    defectiveComponent = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Defective Component text input",
    )

    # ── DEFECT: Radio buttons (value = "YES" or "NO") ───────────────────────
    trial = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Trial Required radio: "YES" or "NO"',
    )
    spares_required = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Spares Required radio: "YES" or "NO"',
    )
    trial_agency = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Trial Agency select (Primary, shown when trial=YES)",
    )
    universal_id_t_dart = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Reference CMMS/SWMM universal id for T_DART",
    )

    # ── DEFECT: File upload ─────────────────────────────────────────────────
    attachPhotograph = EmptyStringFileField(
        required=False,
        allow_null=True,
        help_text="Photograph file upload",
    )

    # ── GUARANTEE DEFECT: Dates ─────────────────────────────────────────────
    g_defectDate = EmptyStringDateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "iso-8601"],
    )
    g_completionDate = EmptyStringDateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "iso-8601"],
    )
    g_repairDate = EmptyStringDateField(
        required=False,
        allow_null=True,
        input_formats=["%Y-%m-%d", "iso-8601"],
    )

    # ── GUARANTEE DEFECT: Text / Selects ────────────────────────────────────
    g_defect_description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Guarantee Defect Description (Primary)",
    )
    g_cause = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Cause / Reason for the Defect",
    )
    g_place = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Place for repair",
    )

    # ── GUARANTEE DEFECT: Radios ────────────────────────────────────────────
    opAvailability = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Op Availability radio: "YES" or "NO"',
    )
    hotWork = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Hot Work radio: "YES" or "NO"',
    )
    g_repairs = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='Repairs select: "0" (NA) or "1" (Date & Place)',
    )

    # ── ASR / ABER: Text inputs ─────────────────────────────────────────────
    aber_type = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='ABER Type radio: "minor", "major", or "aber"',
    )

    asr_desc = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="A's & A's Description textarea (Legacy alias for description)",
    )
    authority = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Authority textarea",
    )
    remarks = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Remarks textarea",
    )

    # ── SPARES: JSON strings (built by JS, sent as hidden input) ────────────
    obs_spares = serializers.CharField(
        required=False,
        allow_blank=True,
        default="[]",
        help_text='JSON string: [{"pattern":"...", "description":"...", "qty":1, "inventory_type":"OBS"}]',
    )
    pil_spares = serializers.CharField(
        required=False,
        allow_blank=True,
        default="[]",
        help_text='JSON string: [{"pattern":"...", "description":"...", "qty":1}]',
    )
    ilms_spares = serializers.CharField(
        required=False,
        allow_blank=True,
        default="[]",
        help_text='JSON string: [{"pattern":"...", "description":"...", "qty":1, "inventory_type":"WED"|"MO"}]',
    )

    # ── Previous DART No (Last Serial) ──────────────────────────────────────
    previous_dart_no = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Previous DART Number/Last Serial",
    )

    # ── Testing only (not in real form — for unauthenticated Swagger) ───────
    department_id = EmptyStringIntegerField(
        required=False,
        allow_null=True,
        help_text="Department ID (for testing without login)",
    )


class MergeDefectsSerializer(serializers.Serializer):
    defect_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class MoveToDraftSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    type = serializers.ChoiceField(choices=["RA", "DL"])


class CompleteDefectSerializer(serializers.Serializer):
    rectified_date = serializers.DateField(required=True)
    repair_agency_code = EmptyStringIntegerField(required=True)
    diagnostic_code = EmptyStringIntegerField(required=False, allow_null=True)
    delay_reason = serializers.CharField(required=False, allow_blank=True)
    days_delay = EmptyStringIntegerField(required=False, default=0, allow_null=True)
    lesson_learnt = serializers.CharField(required=False, allow_blank=True)
    defect_report = EmptyStringFileField(required=False, allow_null=True)

    # JSON Spares or List
    spares_used = serializers.JSONField(
        required=False,
        default=list,
        help_text='JSON array or string: [{"pattern": "", "desc": "", "qty": 1}]',
    )


# ─── POST Request Serializers for Swagger ────────────────────────────────────


class CreateRAAjaxSerializer(serializers.Serializer):
    dart_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="List of DART IDs to create RA for"
    )
    dl_type = serializers.CharField(default="DL-II", help_text="DL Type e.g. DL-II")

    def to_internal_value(self, data):
        import json

        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        if "dart_ids" in mutable_data and isinstance(mutable_data["dart_ids"], str):
            try:
                mutable_data["dart_ids"] = json.loads(mutable_data["dart_ids"])
            except Exception:
                pass
        return super().to_internal_value(mutable_data)


class SaveDLRowSerializer(serializers.Serializer):
    dart_id = serializers.IntegerField(required=False, help_text="InitiateRADL row ID")
    dl_id = serializers.IntegerField(required=False, help_text="InitiateRADL row ID")
    additional_remarks = serializers.CharField(required=False, allow_blank=True)
    additional_remark = serializers.CharField(required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    ss_remark = serializers.CharField(required=False, allow_blank=True)


class SaveDLRowsSerializer(serializers.Serializer):
    rows = SaveDLRowSerializer(many=True, help_text="List of DL rows to save")

    def to_internal_value(self, data):
        import json

        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        if "rows" in mutable_data and isinstance(mutable_data["rows"], str):
            try:
                mutable_data["rows"] = json.loads(mutable_data["rows"])
            except Exception:
                pass
        return super().to_internal_value(mutable_data)


class SaveDLRowsResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=OPERATION_STATUS)
    message = serializers.CharField(help_text=SUCCESS_ERROR)
    data = serializers.DictField(
        required=False, allow_null=True, help_text="Optional extra data"
    )


class ExportPendingDefectsDL2Serializer(serializers.Serializer):
    yard = serializers.CharField(
        help_text="Yard name e.g. ND_MBI, ND_V, NSRY_KOC, NSRY_KAR, NSRY_PBR"
    )
    export_format = serializers.CharField(
        required=False, default="CSV", help_text="Export format e.g. CSV, XLSX"
    )
    refit_Type = serializers.IntegerField(
        required=False, help_text="Refit maintenance period ID"
    )
    row_data = serializers.JSONField(
        help_text="JSON list of DL row objects with assigned dl_number"
    )

    def to_internal_value(self, data):
        import json

        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        if "row_data" in mutable_data and isinstance(mutable_data["row_data"], str):
            try:
                mutable_data["row_data"] = json.loads(mutable_data["row_data"])
            except Exception:
                pass
        return super().to_internal_value(mutable_data)


class ExportPendingDefectsDL2ResponseDataSerializer(serializers.Serializer):
    ra_dl_name = serializers.CharField(
        help_text="Generated DL Group Name e.g. DLII-2-10082026"
    )
    total_records = serializers.IntegerField(help_text="Total DL records processed")
    yard = serializers.CharField(help_text="Yard name")
    download_url = serializers.CharField(help_text="Download URL for exported file")


class ExportPendingDefectsDL2ResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=OPERATION_STATUS)
    message = serializers.CharField(help_text=SUCCESS_ERROR)
    data = ExportPendingDefectsDL2ResponseDataSerializer(
        required=False, allow_null=True
    )


class DeleteDLRowSerializer(serializers.Serializer):
    dl_id = serializers.IntegerField(help_text="DL row ID to delete")


class SaveOEMSpareSerializer(serializers.Serializer):
    pattern_number = serializers.CharField(help_text="Pattern number of the spare")
    description = serializers.CharField(help_text="Spare description")
    denomination_id = serializers.IntegerField(help_text="Denomination FK ID")

    def validate_denomination_id(self, value):
        try:
            return Denomination.objects.get(id=value)
        except Denomination.DoesNotExist:
            raise serializers.ValidationError("Denomination not found")


class CreateRADLFunSerializer(serializers.Serializer):
    defect_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="List of DART defect IDs"
    )


class CreateRADLDefectDataSerializer(serializers.ModelSerializer):
    opra_no = serializers.CharField(source="rha_defect", allow_null=True)
    dart_date = serializers.DateField(format=DATE_FORMAT, allow_null=True)
    rectification_date = serializers.DateField(format=DATE_FORMAT, allow_null=True)
    equipment = serializers.SerializerMethodField()
    nomenclature = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = InitiateDart
        fields = [
            "id",
            "opra_no",
            "dart_number",
            "dart_date",
            "rectification_date",
            "status",
            "equipment",
            "nomenclature",
            "defective_discriptions",
        ]

    def get_equipment(self, obj):
        if obj.equipment_ship and obj.equipment_ship.equipment:
            return str(obj.equipment_ship.equipment.equipment_class)
        if obj.equipment_ems:
            return obj.equipment_ems.name
        return ""

    def get_nomenclature(self, obj):
        if obj.equipment_ship:
            return obj.equipment_ship.nomenclature
        return ""

    def get_status(self, obj):
        return "Closed" if obj.is_closed else "Open"


class CreateRADLFunResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=OPERATION_STATUS)
    message = serializers.CharField(help_text=SUCCESS_ERROR)
    data = CreateRADLDefectDataSerializer(
        many=True, help_text="List of updated DART defects"
    )


class CreateDLFunSerializer(serializers.Serializer):
    dl_defect_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="List of DART defect IDs for DL-II"
    )

    def to_internal_value(self, data):
        import json

        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        if "dl_defect_ids" in mutable_data and isinstance(
            mutable_data["dl_defect_ids"], str
        ):
            try:
                mutable_data["dl_defect_ids"] = json.loads(
                    mutable_data["dl_defect_ids"]
                )
            except Exception:
                pass
        return super().to_internal_value(mutable_data)


class CreateDLRefitItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    actual_start_date = serializers.DateField(allow_null=True)
    actual_end_date = serializers.DateField(allow_null=True)


class CreateDLDefectDataSerializer(serializers.ModelSerializer):
    dart_id = serializers.IntegerField(source="initiate_dart.id")
    dart_number = serializers.CharField(
        source="initiate_dart.dart_number", allow_null=True
    )
    dart_date = serializers.SerializerMethodField()
    defect_closing_date = serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()
    nomenclature = serializers.SerializerMethodField()
    defective_discriptions = serializers.CharField(
        source="initiate_dart.defective_discriptions", allow_null=True
    )

    class Meta:
        model = InitiateRADL
        fields = [
            "id",
            "dl_no",
            "dl_type",
            "status",
            "remarks",
            "additional_remarks",
            "dart_id",
            "dart_number",
            "dart_date",
            "defect_closing_date",
            "equipment",
            "nomenclature",
            "defective_discriptions",
        ]

    def get_dart_date(self, obj):
        dart = obj.initiate_dart
        if dart and dart.dart_date:
            return dart.dart_date.strftime(DATE_FORMAT)
        return None

    def get_defect_closing_date(self, obj):
        dart = obj.initiate_dart
        if dart and dart.rectification_date:
            return dart.rectification_date.strftime(DATE_FORMAT)
        return None

    def get_equipment(self, obj):
        dart = obj.initiate_dart
        if dart:
            if dart.equipment_ship and dart.equipment_ship.equipment:
                return str(dart.equipment_ship.equipment.equipment_class)
            if dart.equipment_ems:
                return dart.equipment_ems.name
        return ""

    def get_nomenclature(self, obj):
        dart = obj.initiate_dart
        if dart and dart.equipment_ship:
            return dart.equipment_ship.nomenclature
        return ""


class CreateDLDataSerializer(serializers.Serializer):
    draft_data = CreateDLDefectDataSerializer(many=True)
    refit_list = CreateDLRefitItemSerializer(many=True)


class CreateDLFunResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=OPERATION_STATUS)
    message = serializers.CharField(help_text=SUCCESS_ERROR)
    data = CreateDLDataSerializer(help_text="Initiated DL draft data and refits list")


class AllDataOfRASerializer(serializers.Serializer):
    yard = serializers.CharField(
        required=False, allow_blank=True, help_text="Yard name"
    )
    export_format = serializers.CharField(
        required=False, allow_blank=True, help_text="Export format e.g. xlsx"
    )
    dart_ids = serializers.ListField(
        child=serializers.IntegerField(), help_text="List of DART IDs"
    )


class ExportPendingDefectsACCDBSerializer(serializers.Serializer):
    yard = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Yard Name e.g. ND (V), NSRY (Koc), ND (Mbi)",
    )
    dtg_date = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="DTG Date e.g. 06-08-2026 or YYYY-MM-DD",
    )
    dtg_hour = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="DTG Hour e.g. 10 or HH",
    )
    dtg_minute = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="DTG Minute e.g. 30 or MM",
    )
    dtg = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Combined DTG string e.g. 2026-08-06 10:30",
    )
    export_format = serializers.CharField(
        required=False,
        allow_blank=True,
        default="CSV",
        help_text="Export format e.g. CSV, XLSX, PDF",
    )
    dart_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        help_text="List of DART IDs e.g. [11]",
    )
    remarks_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text='JSON object mapping dart_id to additional remarks e.g. {"11": "remark text"}',
    )
    dl_type = serializers.CharField(
        required=False, default="RA", help_text="DL Type e.g. RA, DL-II"
    )
    ss_remarks_data = serializers.JSONField(
        required=False,
        default=dict,
        help_text='JSON object mapping dart_id to SS Remarks ID or Code e.g. {"11": "DAN"}',
    )

    def to_internal_value(self, data):
        import json

        mutable_data = data.copy() if hasattr(data, "copy") else dict(data)
        for field_name in ["dart_ids", "remarks_data", "ss_remarks_data"]:
            if field_name in mutable_data and isinstance(mutable_data[field_name], str):
                try:
                    mutable_data[field_name] = json.loads(mutable_data[field_name])
                except Exception:
                    pass
        return super().to_internal_value(mutable_data)


class ExportPendingDefectsACCDBResponseDataSerializer(serializers.Serializer):
    ra_group_id = serializers.CharField(help_text="Generated RA Group ID")
    total_records = serializers.IntegerField(
        help_text="Total number of DART records processed"
    )
    yard = serializers.CharField(help_text="Selected Yard name")
    dtg = serializers.CharField(
        help_text="Combined DTG string", required=False, allow_blank=True
    )
    export_format = serializers.CharField(help_text="Export format e.g. CSV, XLSX")
    dl_type = serializers.CharField(help_text="DL Type e.g. RA")
    download_url = serializers.CharField(
        help_text="Downloadable file URL link e.g. /media/exports/RA_Export_RA-20260810152800.csv"
    )


class ExportPendingDefectsACCDBResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text=OPERATION_STATUS)
    message = serializers.CharField(help_text=SUCCESS_ERROR)
    data = ExportPendingDefectsACCDBResponseDataSerializer(
        required=False, allow_null=True, help_text="RA save / export status details"
    )


class DartHistoryFilteredDataSerializer(serializers.Serializer):
    maintenancePeriod = serializers.CharField(
        required=False, allow_blank=True, help_text="ops or refit"
    )
    dartType = serializers.CharField(
        required=False, allow_blank=True, help_text="Dart type or ALL"
    )
    equipmentSearch = serializers.CharField(
        required=False, allow_blank=True, help_text="Equipment name search"
    )
    subDepartment = serializers.CharField(
        required=False, allow_blank=True, help_text="Sub-department name or ALL"
    )
    department = serializers.CharField(
        required=False, allow_blank=True, help_text="Department name or ALL"
    )
    defectDateFrom = serializers.CharField(
        required=False, allow_blank=True, help_text="YYYY-MM-DD"
    )
    defectDateTo = serializers.CharField(
        required=False, allow_blank=True, help_text="YYYY-MM-DD"
    )


class RefitOccasionCreateSerializer(serializers.Serializer):
    """POST: Create a new refit/operational period."""

    start_date = serializers.CharField(help_text="YYYY-MM-DD")
    completion_date = serializers.CharField(help_text="YYYY-MM-DD")
    refit_type = serializers.CharField(help_text="AMP, SMP, EAMP, NR, MR, SR etc.")


class RefitOccasionEditSerializer(serializers.Serializer):
    """PUT: Edit dates of an existing refit/operational period."""

    period_id = serializers.IntegerField(help_text="ID of the period to edit")
    start_date = serializers.CharField(help_text="YYYY-MM-DD")
    completion_date = serializers.CharField(help_text="YYYY-MM-DD")


# ─── GET / POST Response Serializers for Swagger ─────────────────────────────


class GetRefitPeriodsResponseSerializer(serializers.Serializer):
    value = serializers.CharField(help_text="Year label value")
    label = serializers.CharField(help_text="Year label display")


class DeleteDLRowResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="success or error")
    message = serializers.CharField(help_text="Operation result message")


@extend_schema_serializer(component_name="DartGetEquipmentDetailsResponse")
class GetEquipmentDetailsResponseSerializer(serializers.Serializer):
    equipment_code = serializers.CharField(help_text="Equipment code")
    nomenclatures = serializers.ListField(
        child=serializers.CharField(), help_text="List of nomenclatures"
    )


class ShipEquipmentSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nomenclature = serializers.CharField()


class GetEquipmentObjectsResponseSerializer(serializers.Serializer):
    ship_equipments = ShipEquipmentSimpleSerializer(many=True)


class GetNomenclatureDetailsResponseSerializer(serializers.Serializer):
    equipment_serial_no = serializers.CharField()
    equipment_id = serializers.IntegerField()
    location_on_board = serializers.CharField()
    department = serializers.CharField()
    sub_department = serializers.CharField()
    prev_dart_no = serializers.CharField()


class GetDartSpareItemSerializer(serializers.Serializer):
    pattern = serializers.CharField()
    description = serializers.CharField()
    inventory_type = serializers.CharField()
    quantity = serializers.IntegerField()


class GetDartDetailsResponseDataSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dart_number = serializers.CharField()
    dart_date = serializers.CharField()
    rectification_date = serializers.CharField()
    description = serializers.CharField()
    spares = GetDartSpareItemSerializer(many=True)


class GetDartDetailsResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = GetDartDetailsResponseDataSerializer()


class SubDeptDefectItemSerializer(serializers.Serializer):
    dart_number = serializers.CharField()
    nomenclature = serializers.CharField()
    category = serializers.CharField()
    defective_since = serializers.CharField()


class GetSubDeptDefectsResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = SubDeptDefectItemSerializer(many=True)


class DartHistoryItemSerializer(serializers.Serializer):
    dartNo = serializers.CharField()
    cmmsSyncStatus = serializers.BooleanField()
    opraNo = serializers.CharField()
    raRaised = serializers.BooleanField()
    dlNo = serializers.CharField()
    dlRaised = serializers.BooleanField()
    equipmentName = serializers.CharField()
    equipmentNomenclature = serializers.CharField()
    defectDescription = serializers.CharField()
    subDepartment = serializers.CharField()
    dartOccasion = serializers.CharField()
    defectDate = serializers.CharField()
    shipRemarks = serializers.CharField()
    id = serializers.IntegerField()
    maintenanceType = serializers.CharField()
    refitType = serializers.CharField()


class DartHistoryFilteredDataResponseSerializer(serializers.Serializer):
    data = DartHistoryItemSerializer(many=True)


class GetDartSparesItemSerializer(serializers.Serializer):
    item_code = serializers.CharField(required=False, allow_blank=True)
    item_desc = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    crp_category = serializers.CharField(required=False, allow_blank=True)
    denomination = serializers.CharField(required=False, allow_blank=True)
    price = serializers.CharField(required=False, allow_blank=True)
    price_date = serializers.CharField(required=False, allow_blank=True)
    ilms_eqpt_code = serializers.CharField(required=False, allow_blank=True)
    ilms_eqpt_desc = serializers.CharField(required=False, allow_blank=True)
    vendor_name = serializers.CharField(required=False, allow_blank=True)
    eqpt = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    typeofspare = serializers.CharField(required=False, allow_blank=True)
    avail_status = serializers.CharField(required=False, allow_blank=True)
    wed_eqpt_name = serializers.CharField(required=False, allow_blank=True)
    sfd_equipment = serializers.CharField(required=False, allow_blank=True)
    held_qty = serializers.IntegerField(required=False, allow_null=True)
    authority = serializers.CharField(required=False, allow_blank=True)

    # camelCase keys for OBS / Mapped-OBS
    equipmentClass = serializers.CharField(required=False, allow_blank=True)
    patternNo = serializers.CharField(required=False, allow_blank=True)
    itemDesc = serializers.CharField(required=False, allow_blank=True)
    availabilityStatus = serializers.CharField(required=False, allow_blank=True)
    heldQty = serializers.IntegerField(required=False, allow_null=True)
    crpCategory = serializers.CharField(required=False, allow_blank=True)

    pk = serializers.CharField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Only return keys that are explicitly present in the input dictionary
        return {k: v for k, v in ret.items() if k in instance}


class GetDartSparesDataResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = GetDartSparesItemSerializer(many=True)


class DartHistoryDetailDefectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dart_number = serializers.CharField()
    dart_date = serializers.CharField()
    defective_discriptions = serializers.CharField()
    maintenance_period = serializers.CharField()
    dart_occasion = serializers.CharField()
    is_closed = serializers.BooleanField()


class DartHistoryDetailClosureSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    serial_no = serializers.CharField()
    rectified_date = serializers.CharField()
    days_delay = serializers.IntegerField()
    lesson_learnt = serializers.CharField()
    other_reasons = serializers.CharField()
    repair_agency_code_id = serializers.IntegerField(required=False, allow_null=True)
    diagnostic_code_id = serializers.IntegerField(required=False, allow_null=True)
    repair_code_id = serializers.IntegerField(required=False, allow_null=True)
    delay_code_id = serializers.IntegerField(required=False, allow_null=True)
    spares_delay = serializers.IntegerField(required=False, allow_null=True)


class DartHistoryDetailSpareUsedSerializer(serializers.Serializer):
    pattern_no = serializers.CharField()
    description = serializers.CharField()
    quantity = serializers.IntegerField()


class DartHistoryDetailRADLEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dl_type = serializers.CharField()
    dl_key = serializers.CharField()
    status = serializers.CharField()
    remarks = serializers.CharField()


class DartHistoryDetailResponseSerializer(serializers.Serializer):
    defect = DartHistoryDetailDefectSerializer()
    closure = DartHistoryDetailClosureSerializer(allow_null=True)
    spares_used = DartHistoryDetailSpareUsedSerializer(many=True)
    ra_dl_entries = DartHistoryDetailRADLEntrySerializer(many=True)


class MaintenancePeriodItemSerializer(serializers.Serializer):
    maintenance_period = serializers.CharField()
    occasion = serializers.CharField()
    start_date = serializers.CharField()
    end_date = serializers.CharField()
    is_current = serializers.BooleanField()


class MaintenanceOverviewCardSerializer(serializers.Serializer):
    value = serializers.IntegerField()
    status = serializers.CharField(required=False, allow_null=True)
    change_percentage = serializers.IntegerField(required=False, allow_null=True)


class MaintenanceOverviewSerializer(serializers.Serializer):
    operational_readiness = MaintenanceOverviewCardSerializer()
    critical_defects = MaintenanceOverviewCardSerializer()
    overdue_maintops = MaintenanceOverviewCardSerializer()
    equipment_under_maintenance = MaintenanceOverviewCardSerializer()
    repeated_failures = MaintenanceOverviewCardSerializer()


class AllPeriodsMaintenanceOverviewSerializer(serializers.Serializer):
    six_m = MaintenanceOverviewSerializer(source="6M")
    one_y = MaintenanceOverviewSerializer(source="1Y")
    two_y = MaintenanceOverviewSerializer(source="2Y")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "6M": data.get("six_m"),
            "1Y": data.get("one_y"),
            "2Y": data.get("two_y"),
        }


class MaintenanceOverviewKPIResponseSerializer(serializers.Serializer):
    kpis = serializers.ListField(child=serializers.DictField())
    periods = serializers.ListField(child=serializers.CharField(), required=False)
    default_period = serializers.CharField(required=False)


class CommandActionItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    count = serializers.IntegerField()
    severity = serializers.CharField()


class CommandActionsPendingSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    items = CommandActionItemSerializer(many=True)


class MaintenancePrioritisationItemSerializer(serializers.Serializer):
    icon = serializers.CharField(allow_blank=True)
    title = serializers.CharField()
    sub_title = serializers.CharField()
    priority = serializers.CharField()
    percentage = serializers.IntegerField()


class MaintenancePrioritisationSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    maintenance_prioritisation_items = MaintenancePrioritisationItemSerializer(
        many=True
    )


class EquipmentHealthSummarySerializer(serializers.Serializer):
    equipment_id = serializers.CharField()
    equipment_name = serializers.CharField()
    score = serializers.IntegerField()
    status = serializers.CharField()
    alarm_count = serializers.IntegerField()
    message = serializers.CharField()


class EquipmentConditionParameterSerializer(serializers.Serializer):
    parameter = serializers.CharField()
    current_value = serializers.IntegerField()
    unit = serializers.CharField(allow_blank=True)
    trend_data = serializers.ListField(child=serializers.IntegerField())


class SelectedEquipmentHealthSerializer(serializers.Serializer):
    equipment_name = serializers.CharField(allow_blank=True)
    system = serializers.CharField()
    location = serializers.CharField()
    image = serializers.CharField(allow_blank=True)
    condition_parameters = EquipmentConditionParameterSerializer(many=True)


class EquipmentHealthMonitoringSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    search_enabled = serializers.BooleanField()
    equipment_summary = EquipmentHealthSummarySerializer(many=True)
    selected_equipment = SelectedEquipmentHealthSerializer()


class MovementConfigurationHistoryItemSerializer(serializers.Serializer):
    date = serializers.CharField()
    event_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()


class MovementConfigurationHistorySerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    movement_and_configuration_histories = MovementConfigurationHistoryItemSerializer(
        many=True
    )


class MaintenanceConstraintSummarySerializer(serializers.Serializer):
    spares_constraints = serializers.IntegerField()
    fmu_oem_dependencies = serializers.IntegerField()
    trials_pending = serializers.IntegerField()
    manpower_gaps = serializers.IntegerField()


class MaintenanceConstraintItemSerializer(serializers.Serializer):
    constraint_type = serializers.CharField()
    description = serializers.CharField()
    reference_id = serializers.CharField(allow_blank=True)


class MaintenanceConstraintsDependenciesSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    summary = MaintenanceConstraintSummarySerializer()
    constraints = MaintenanceConstraintItemSerializer(many=True)


class DashboardMetricSerializer(serializers.Serializer):
    title = serializers.CharField()
    value = serializers.IntegerField()
    unit = serializers.CharField()
    trend_data = serializers.ListField(child=serializers.IntegerField())


class ContextualSearchDrillDownSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    search_enabled = serializers.BooleanField()
    metrics = DashboardMetricSerializer(many=True)


class ReliabilityMetricSerializer(serializers.Serializer):
    metric_name = serializers.CharField()
    value = serializers.IntegerField()
    unit = serializers.CharField()
    trend_data = serializers.ListField(child=serializers.IntegerField())


class ReliabilityDegradationTrendSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    search_enabled = serializers.BooleanField()
    metrics = ReliabilityMetricSerializer(many=True)


class TrialsValidationSummarySerializer(serializers.Serializer):
    restored = serializers.IntegerField()
    validation_pending = serializers.IntegerField()
    failed = serializers.IntegerField()


class TrialValidationActivitySerializer(serializers.Serializer):
    equipment_name = serializers.CharField()
    activity = serializers.CharField()
    date = serializers.CharField()
    status = serializers.CharField()


class TrialsValidationPostMaintenanceSerializer(serializers.Serializer):
    heading = serializers.CharField()
    view_all_flag = serializers.BooleanField()
    summary = TrialsValidationSummarySerializer()
    activities = TrialValidationActivitySerializer(many=True)


class MaintenanceOverviewDetailsSerializer(serializers.Serializer):
    command_actions_pending = CommandActionsPendingSerializer()
    maintenance_prioritisation = MaintenancePrioritisationSerializer()
    equipment_health_monitoring = EquipmentHealthMonitoringSerializer()
    movement_and_configuration_history = MovementConfigurationHistorySerializer()
    maintenance_constraints_and_dependencies = (
        MaintenanceConstraintsDependenciesSerializer()
    )
    contextual_search_and_drill_down = ContextualSearchDrillDownSerializer()
    reliability_and_degradation_trend = ReliabilityDegradationTrendSerializer()
    trials_validation_and_post_maintenance = TrialsValidationPostMaintenanceSerializer()


class CompleteDefectGETDetailSerializer(serializers.ModelSerializer):
    equipment_name = serializers.SerializerMethodField()
    nomenclature = serializers.SerializerMethodField()
    sub_dept = serializers.SerializerMethodField()
    defect_date = serializers.SerializerMethodField()
    defect_closing_date = serializers.SerializerMethodField()
    scheduled_date = serializers.SerializerMethodField()

    class Meta:
        model = InitiateDart
        fields = [
            "id",
            "dart_number",
            "equipment_name",
            "nomenclature",
            "sub_dept",
            "defect_date",
            "defect_closing_date",
            "scheduled_date",
            "defective_discriptions",
        ]

    def get_equipment_name(self, obj):
        if obj.equipment_ship and obj.equipment_ship.equipment:
            return obj.equipment_ship.equipment.equipment_class
        if obj.equipment_ems:
            return obj.equipment_ems.name
        return ""

    def get_nomenclature(self, obj):
        if obj.equipment_ship:
            return obj.equipment_ship.nomenclature
        return ""

    def get_equipment_nomenclature(self, obj):
        return self.get_nomenclature(obj)

    def get_sub_dept(self, obj):
        if obj.equipment_ship and obj.equipment_ship.sub_department_f_key:
            return obj.equipment_ship.sub_department_f_key.name
        return ""

    def get_defect_date(self, obj):
        d = obj.dart_date or obj.created_date
        return d.strftime("%d %b %Y") if d else ""

    def get_defect_closing_date(self, obj):
        from datetime import date

        return date.today().strftime("%d %b %Y")

    def get_scheduled_date(self, obj):
        return (
            obj.rectification_date.strftime("%d %b %Y")
            if obj.rectification_date
            else ""
        )


class IssuedSpareSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk", required=False)
    spare_pattern_number = serializers.CharField(
        source="spare.pattern_number", default=""
    )
    spare_description = serializers.CharField(source="spare.description", default="")
    pattern = serializers.CharField(source="spare.pattern_number", default="")
    description = serializers.CharField(source="spare.description", default="")
    quantity_issued = serializers.IntegerField(default=0)
    quantity = serializers.IntegerField(source="quantity_issued", default=0)
    date_of_issue = serializers.DateField(allow_null=True)


class CompleteDefectGETDataSerializer(serializers.Serializer):
    defect = CompleteDefectGETDetailSerializer()
    issued_spare_obj = IssuedSpareSerializer(many=True)
    repair_agency_list = serializers.ListField(child=serializers.DictField())
    diagnostic_list = serializers.ListField(child=serializers.DictField())
    repair_list = serializers.ListField(child=serializers.DictField())
    delay_list = serializers.ListField(child=serializers.DictField())


class CompleteDefectGETResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Status, e.g. success")
    message = serializers.CharField(help_text="Message")
    data = CompleteDefectGETDataSerializer(
        help_text="Details for defect completion form"
    )


class CompleteDefectPOSTResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Status, e.g. success")
    message = serializers.CharField(help_text="Message")
    data = serializers.DictField(allow_null=True, required=False)


# ─────────────────────────────────────────────────────────────
# CMMS / CANDEF / OPDEF Integration Serializers
# ─────────────────────────────────────────────────────────────


class GenericSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField(required=False, default=None, allow_null=True)


class DefectCreateSerializer(serializers.Serializer):
    symptom_code_id = serializers.IntegerField(required=False, allow_null=True)
    severity_code_id = serializers.IntegerField(required=False, allow_null=True)
    remark_code_id = serializers.IntegerField(required=False, allow_null=True)
    require_assistance_for_code_id = serializers.IntegerField(
        required=False, allow_null=True
    )
    equipment_ship_id = serializers.IntegerField(required=False, allow_null=True)
    department_id_id = serializers.IntegerField(required=False, allow_null=True)
    equipment_ems_id = serializers.IntegerField(required=False, allow_null=True)
    dart_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    dart_sr_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    dart_date = serializers.DateField(required=False, allow_null=True)
    rectification_date = serializers.DateField(required=False, allow_null=True)
    ops_status = serializers.BooleanField(required=False, allow_null=True)
    trial_required = serializers.BooleanField(required=False, allow_null=True)
    defective_discriptions = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    defective_component = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    RHA_defect = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    maintenance_period = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    dart_occasion = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    is_guarantee_defect = serializers.BooleanField(required=False, default=False)


class DefectResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dart_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    dart_sr_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    dart_date = serializers.DateField(required=False, allow_null=True)
    rectification_date = serializers.DateField(required=False, allow_null=True)
    is_closed = serializers.BooleanField(default=False)
    defective_discriptions = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    defective_component = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    maintenance_period = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    is_guarantee_defect = serializers.BooleanField(default=False)
    created_date = serializers.DateField(required=False, allow_null=True)


class DefectRectifyRequestSerializer(serializers.Serializer):
    serial_no = serializers.CharField(required=True)
    rectified_date = serializers.DateField(required=True)
    repair_agency_code_id = serializers.IntegerField(required=False, allow_null=True)
    diagnostic_code_id = serializers.IntegerField(required=False, allow_null=True)
    repair_code_id = serializers.IntegerField(required=False, allow_null=True)
    delay_code_id = serializers.IntegerField(required=False, allow_null=True)
    days_delay = serializers.IntegerField(required=False, allow_null=True)
    spares_delay = serializers.IntegerField(required=False, allow_null=True)
    other_reasons = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    lesson_learnt = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class CmmsDartPayloadResponseSerializer(serializers.Serializer):
    M_Diagnostic = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_Refit = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_Ship = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_group = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_department = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_repair_agency = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=[],
        source="M_repair agency",
    )
    M_Delay = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_Repair = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_section = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_DART = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )


class CompletedRoutineCreateSerializer(serializers.Serializer):
    routine_id = serializers.IntegerField(required=True)
    old_dart_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )
    new_dart_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )
    date_of_completion = serializers.DateField(required=False, allow_null=True)
    hours = serializers.IntegerField(required=False, allow_null=True)
    minutes = serializers.IntegerField(required=False, allow_null=True)
    carried_by = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    p_no = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    running_hour = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    due_running_hour = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    completion_details = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class CompletedRoutineResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    routine_id = serializers.IntegerField(required=False, allow_null=True)
    old_dart_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    new_dart_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    date_of_completion = serializers.DateField(required=False, allow_null=True)
    hours = serializers.IntegerField(required=False, allow_null=True)
    minutes = serializers.IntegerField(required=False, allow_null=True)
    carried_by = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    running_hour = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    completion_details = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class OpdefInitiateRequestSerializer(serializers.Serializer):
    ship_id = serializers.IntegerField(required=True)
    fitted_equipment_id = serializers.IntegerField(required=True)
    opdef_number = serializers.CharField(required=True)
    opdef_date = serializers.DateField(required=True)
    operational_impact = serializers.CharField(required=True)
    department_id = serializers.IntegerField(required=True)
    defect_description = serializers.CharField(required=True)


class OpdefInitiateResponseSerializer(serializers.Serializer):
    OpdefMainID = serializers.IntegerField()
    Universal_ID_T_OpdefMain = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class OpdefAnalysisRequestSerializer(serializers.Serializer):
    analysis_date = serializers.DateField(required=True)
    failure_cause = serializers.CharField(required=True)
    rectification_method_proposed = serializers.CharField(required=True)
    analysed_by = serializers.CharField(required=True)


class OpdefSpareRequestSerializer(serializers.Serializer):
    spare_item_code = serializers.CharField(required=True)
    nomenclature = serializers.CharField(required=True)
    quantity_consumed = serializers.IntegerField(required=True)
    unit_cost = serializers.FloatField(required=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class OpdefTrialRequestSerializer(serializers.Serializer):
    trial_date = serializers.DateField(required=True)
    rpm_reading = serializers.IntegerField(required=True)
    temperature_celsius = serializers.FloatField(required=True)
    vibration_velocity_mms = serializers.FloatField(required=True)
    status = serializers.CharField(required=True)


class OpdefPriorParamRequestSerializer(serializers.Serializer):
    reading_time = serializers.DateTimeField(required=True)
    rpm_reading = serializers.IntegerField(required=True)
    temperature_celsius = serializers.FloatField(required=True)
    vibration_velocity_mms = serializers.FloatField(required=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class OpdefPhotoResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    file_path = serializers.CharField()
    message = serializers.CharField()


class OpdefSyncPayloadResponseSerializer(serializers.Serializer):
    T_OpdefMain = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_opdefgeneratinfo = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_DefectAnalysis = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_MajorSpareconsumer = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_trailconductedParameter = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_opdefpriorparameter = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_photograph = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )


class DartHistoryItemSerializer(serializers.Serializer):
    dartNo = serializers.CharField()
    cmmsSyncStatus = serializers.BooleanField()
    opraNo = serializers.CharField()
    raRaised = serializers.BooleanField()
    dlNo = serializers.CharField()
    dlRaised = serializers.BooleanField()
    equipmentName = serializers.CharField()
    equipmentNomenclature = serializers.CharField()
    defectDescription = serializers.CharField()
    subDepartment = serializers.CharField()
    dartOccasion = serializers.CharField()
    defectDate = serializers.CharField()
    shipRemarks = serializers.CharField()
    id = serializers.IntegerField()
    maintenanceType = serializers.CharField()
    refitType = serializers.CharField()


class DartHistoryFiltersSerializer(serializers.Serializer):
    dartMaintenancePeriod = serializers.ListField(child=serializers.CharField())
    dartOccasions = serializers.ListField(child=serializers.CharField())
    subDepartments = serializers.ListField(child=serializers.CharField())
    dartTypes = serializers.ListField(child=serializers.CharField())
    departments = serializers.ListField(child=serializers.CharField())
    equipments = serializers.ListField(child=serializers.CharField())
    equipmentNomenclatures = serializers.ListField(child=serializers.CharField())


class DartHistoryDefaultDataResponseSerializer(serializers.Serializer):
    data = DartHistoryItemSerializer(many=True)
    filters = DartHistoryFiltersSerializer()
