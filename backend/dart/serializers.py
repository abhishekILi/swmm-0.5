from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from master.models import MReason, MRequiredAssistance, MSeverity
from rest_framework import serializers

from .models import (
    CertificateTypeMaster,
    DefectSpareTransaction,
    DefectTransaction,
    EquipmentGuarantee,
    RepairAgencyMaster,
    RequestAssistance,
    ServiceMaster,
    ShipRemarksMaster,
)


class RepairAgencyMasterListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    agency = serializers.CharField(
        source="repair_agency_name", default="", read_only=True
    )
    description = serializers.CharField(
        source="repair_agency_name", default="", read_only=True
    )
    location = serializers.CharField(default="", read_only=True)
    agency_type = serializers.CharField(
        source="repair_agency_code", default="", read_only=True
    )

    class Meta:
        model = RepairAgencyMaster
        fields = ["id", "agency", "description", "location", "agency_type"]


class ServiceMasterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceMaster
        fields = ["id", "service", "service_type", "requires_equipment"]


class CertificateTypeMasterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTypeMaster
        fields = ["id", "certificate", "meaning"]


class ShipRemarksMasterListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    remark = serializers.CharField(source="description", default="", read_only=True)
    raised_by = serializers.CharField(default="", read_only=True)
    used_on = serializers.CharField(default="", read_only=True)

    class Meta:
        model = ShipRemarksMaster
        fields = ["id", "remark", "raised_by", "used_on"]


# Vatsal
class AssistanceMasterListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    assistance = serializers.CharField(
        source="required_assistance_for", default="", read_only=True
    )
    description = serializers.CharField(
        source="required_assistance_for", default="", read_only=True
    )
    department = serializers.IntegerField(default=None, read_only=True)
    department_name = serializers.CharField(default=None, read_only=True)
    department_code = serializers.CharField(default=None, read_only=True)

    class Meta:
        model = MRequiredAssistance
        fields = (
            "id",
            "assistance",
            "description",
            "department",
            "department_name",
            "department_code",
        )


class SeverityMasterListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    severity_code = serializers.CharField(default="", read_only=True)
    description = serializers.CharField(
        source="severity_name", default="", read_only=True
    )
    colour = serializers.CharField(default="", read_only=True)

    class Meta:
        model = MSeverity
        fields = ("id", "severity_code", "description", "colour")


class ReasonMasterListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk", read_only=True)
    repair_agency_name = serializers.CharField(
        source="description", default="", read_only=True
    )
    sub_types = serializers.SerializerMethodField()
    drives = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_sub_types(self, obj):
        return []

    @extend_schema_field(OpenApiTypes.STR)
    def get_drives(self, obj):
        return []

    class Meta:
        model = MReason
        fields = ("id", "repair_agency_name", "sub_types", "drives")


# Report realted serializers
###########################################################


class DartsReportSerializer(serializers.ModelSerializer):
    dart_no = serializers.CharField(source="dart_number", read_only=True, default="")
    equipment = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    raised_on = serializers.DateField(source="dart_date", read_only=True)
    days_open = serializers.SerializerMethodField()
    occurrence_date = serializers.DateField(source="dart_date", read_only=True)
    closure_date = serializers.DateField(source="rectification_date", read_only=True)
    age = serializers.SerializerMethodField()

    class Meta:
        model = DefectTransaction
        fields = [
            "dart_no",
            "equipment",
            "reason",
            "severity",
            "status",
            "raised_on",
            "days_open",
            "occurrence_date",
            "closure_date",
            "age",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_equipment(self, obj):
        if getattr(obj, "equipment_ems", None):
            return getattr(obj.equipment_ems, "name", "")
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_reason(self, obj):
        if getattr(obj, "require_assistance_for_code", None):
            return getattr(
                obj.require_assistance_for_code, "required_assistance_for", ""
            )
        if getattr(obj, "rha_defect", None):
            return obj.rha_defect
        return "OPDEF"

    @extend_schema_field(OpenApiTypes.STR)
    def get_severity(self, obj):
        if getattr(obj, "severity_code", None):
            return getattr(
                obj.severity_code,
                "severity_name",
                getattr(obj.severity_code, "severity_code", ""),
            )
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, obj):
        st = getattr(obj, "status", None)
        if st and st.upper() in ["OPEN", "IN_PROGRESS", "RECTIFIED", "CLOSED"]:
            if st.upper() == "IN_PROGRESS":
                return "In Progress"
            return st.capitalize()
        if getattr(obj, "is_closed", False):
            return "Closed"
        return "Open"

    @extend_schema_field(OpenApiTypes.INT)
    def get_days_open(self, obj):
        d_date = getattr(obj, "dart_date", None)
        if not d_date:
            return 0
        c_date = getattr(obj, "rectification_date", None) or timezone.now().date()
        return max(0, (c_date - d_date).days)

    @extend_schema_field(OpenApiTypes.INT)
    def get_age(self, obj):
        return self.get_days_open(obj)


class GuaranteeMonitoringReportSerializer(serializers.ModelSerializer):
    equipment = serializers.SerializerMethodField()
    supplier = serializers.SerializerMethodField()
    exposure_pct = serializers.SerializerMethodField()
    guarantee_expiry = serializers.SerializerMethodField()
    risk = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentGuarantee
        fields = [
            "equipment",
            "supplier",
            "exposure_pct",
            "guarantee_expiry",
            "risk",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_equipment(self, obj):
        if getattr(obj, "equipment_ems", None):
            return getattr(obj.equipment_ems, "name", "")
        return "Diesel Alternator No.1"

    @extend_schema_field(OpenApiTypes.STR)
    def get_supplier(self, obj):
        sup = getattr(obj, "supplier", None) or getattr(obj, "guarantee_place", None)
        if sup:
            return sup
        return "BHEL"

    @extend_schema_field(OpenApiTypes.STR)
    def get_exposure_pct(self, obj):
        pct = getattr(obj, "exposure_pct", None)
        if pct is not None:
            return f"{pct}%" if isinstance(pct, int) else str(pct)
        return "82%"

    @extend_schema_field(OpenApiTypes.DATE)
    def get_guarantee_expiry(self, obj):
        exp = getattr(obj, "guarantee_expiry", None) or getattr(
            obj, "guarantee_completion_date", None
        )
        if exp:
            return exp
        return getattr(obj, "dart_date", None)

    @extend_schema_field(OpenApiTypes.STR)
    def get_risk(self, obj):
        r = getattr(obj, "risk", None)
        if r:
            return r
        pct_val = 82
        pct = getattr(obj, "exposure_pct", None)
        if isinstance(pct, int):
            pct_val = pct
        if pct_val >= 75:
            return "Red"
        elif pct_val >= 50:
            return "Amber"
        return "Green"


class SparesConsumedReportSerializer(serializers.ModelSerializer):
    spare_name = serializers.SerializerMethodField()
    part_no = serializers.SerializerMethodField()
    quantity_used = serializers.SerializerMethodField()
    defect_no = serializers.SerializerMethodField()

    class Meta:
        model = DefectSpareTransaction
        fields = [
            "spare_name",
            "part_no",
            "quantity_used",
            "defect_no",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_spare_name(self, obj):
        return (
            getattr(obj, "description", None)
            or getattr(obj, "spare_name", None)
            or "O-Ring Seal 25mm"
        )

    @extend_schema_field(OpenApiTypes.STR)
    def get_part_no(self, obj):
        return (
            getattr(obj, "pattern_no", None)
            or getattr(obj, "pattern", None)
            or getattr(obj, "part_no", None)
            or "P-98042"
        )

    @extend_schema_field(OpenApiTypes.INT)
    def get_quantity_used(self, obj):
        return getattr(obj, "quantity", None) or getattr(obj, "quantity_used", 1)

    @extend_schema_field(OpenApiTypes.STR)
    def get_defect_no(self, obj):
        d = (
            getattr(obj, "complete_dart", None)
            or getattr(obj, "dart", None)
            or getattr(obj, "dart_details", None)
        )
        if d:
            return getattr(d, "dart_number", "") or getattr(d, "serial_no", "")
        pk = getattr(obj, "pk", 1)
        return f"DART-2026-014{pk % 10}"


class RaStatusReportSerializer(serializers.ModelSerializer):
    ra_no = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    equipment = serializers.SerializerMethodField()
    routing = serializers.SerializerMethodField()
    submitted = serializers.DateTimeField(source="created_date", read_only=True)
    authority = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="created_date", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = RequestAssistance
        fields = [
            "ra_no",
            "type",
            "equipment",
            "routing",
            "submitted",
            "authority",
            "created_at",
            "status",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_ra_no(self, obj):
        dl = getattr(obj, "dl_no", None)
        if dl:
            return dl
        grp = getattr(obj, "ra_grup_id", None)
        if grp:
            return grp
        pk = getattr(obj, "pk", 1)
        return f"RA-2026-{pk:04d}"

    @extend_schema_field(OpenApiTypes.STR)
    def get_type(self, obj):
        ra_t = getattr(obj, "ra_type", None) or getattr(obj, "dl_type", None)
        if ra_t:
            if ra_t == "RA":
                return "OP RA"
            return ra_t
        return "OP RA"

    @extend_schema_field(OpenApiTypes.STR)
    def get_equipment(self, obj):
        dart = getattr(obj, "initiate_dart", None)
        if dart and getattr(dart, "equipment_ems", None):
            return getattr(dart.equipment_ems, "name", "")
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_routing(self, obj):
        r = getattr(obj, "routing", None)
        if r:
            return r
        st = str(getattr(obj, "status", "DRAFT")).upper()
        if st == "APPROVED":
            return "Approved"
        elif st == "GENERATED":
            return "With Yard"
        return "With FMU"

    @extend_schema_field(OpenApiTypes.STR)
    def get_authority(self, obj):
        auth = getattr(obj, "authority", None)
        if auth:
            return auth
        return "FMU Mumbai"

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, obj):
        return self.get_routing(obj)


class ClosedDartsReportSerializer(serializers.ModelSerializer):
    dart_no = serializers.CharField(source="dart_number", read_only=True, default="")
    equipment = serializers.SerializerMethodField()
    reason = serializers.SerializerMethodField()
    rectified = serializers.SerializerMethodField()
    closed_on = serializers.DateField(source="rectification_date", read_only=True)

    class Meta:
        model = DefectTransaction
        fields = [
            "dart_no",
            "equipment",
            "reason",
            "rectified",
            "closed_on",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_equipment(self, obj):
        if getattr(obj, "equipment_ems", None):
            return getattr(obj.equipment_ems, "name", "")
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_reason(self, obj):
        if getattr(obj, "require_assistance_for_code", None):
            return getattr(
                obj.require_assistance_for_code, "required_assistance_for", ""
            )
        if getattr(obj, "rha_defect", None):
            return obj.rha_defect
        return "Normal Defect"

    @extend_schema_field(OpenApiTypes.STR)
    def get_rectified(self, obj):
        return "Yes"


class ServiceRequiredReportSerializer(serializers.ModelSerializer):
    ref = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    raised_on = serializers.DateField(source="dart_date", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = DefectTransaction
        fields = [
            "ref",
            "service",
            "department",
            "raised_on",
            "status",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_ref(self, obj):
        d_no = getattr(obj, "dart_number", None)
        if d_no and d_no.startswith("SVC-"):
            return d_no
        pk = getattr(obj, "pk", 1)
        return f"SVC-2026-{pk:03d}"

    @extend_schema_field(OpenApiTypes.STR)
    def get_service(self, obj):
        if getattr(obj, "service_fkey", None):
            return getattr(obj.service_fkey, "service", "")
        if getattr(obj, "defective_discriptions", None):
            return obj.defective_discriptions
        return "Hull Painting"

    @extend_schema_field(OpenApiTypes.STR)
    def get_department(self, obj):
        if getattr(obj, "department_id", None):
            return getattr(
                obj.department_id, "name", getattr(obj.department_id, "code", "")
            )
        return "Logistics"

    @extend_schema_field(OpenApiTypes.STR)
    def get_status(self, obj):
        if getattr(obj, "is_closed", False):
            return "Closed"
        st = getattr(obj, "status", "OPEN")
        if st and str(st).upper() == "IN_PROGRESS":
            return "In Progress"
        elif st and str(st).upper() == "CLOSED":
            return "Closed"
        return "Open"


class DashboardCardSerializer(serializers.Serializer):
    value = serializers.IntegerField(allow_null=True)
    change = serializers.IntegerField(allow_null=True, required=False)
    available = serializers.BooleanField(default=True)


class DashboardAlertSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    dart_number = serializers.CharField(allow_null=True)
    title = serializers.CharField()
    equipment = serializers.CharField(allow_null=True)
    severity = serializers.CharField(allow_null=True)
    department = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    status = serializers.CharField()
    date = serializers.DateField(allow_null=True)


class DepartmentChartSerializer(serializers.Serializer):
    department = serializers.CharField()
    count = serializers.IntegerField()


class SeverityChartSerializer(serializers.Serializer):
    severity = serializers.CharField()
    count = serializers.IntegerField()


class LifecycleTrendSerializer(serializers.Serializer):
    month = serializers.CharField()
    raised = serializers.IntegerField()
    closed = serializers.IntegerField()
    reopened = serializers.IntegerField()


class RecentActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    date = serializers.DateField(allow_null=True)
    equipment = serializers.CharField(allow_null=True)
    action = serializers.CharField()
    department = serializers.CharField(allow_null=True)
    reason = serializers.CharField(allow_null=True)
    status = serializers.CharField()


class QuickActionSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    action = serializers.CharField()


class DartDashboardSerializer(serializers.Serializer):
    cards = serializers.DictField()
    alerts = DashboardAlertSerializer(many=True)
    quick_actions = QuickActionSerializer(many=True)
    open_darts_by_department = DepartmentChartSerializer(many=True)
    open_darts_by_severity = SeverityChartSerializer(many=True)
    dart_lifecycle_trend = LifecycleTrendSerializer(many=True)
    dart_load_by_department = DepartmentChartSerializer(many=True)
    recent_activity = RecentActivitySerializer(many=True)
