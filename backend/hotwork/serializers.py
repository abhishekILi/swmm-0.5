"""
Serializers for hotwork_drf.

HotworkSerializer/HotworkHODApprovalSerializer are ModelSerializers used for
list/retrieve/approval-list output -- they replace the ad hoc
attribute-bolting the legacy views did onto AddHotwork instances in a Python
loop (hotwork.ship = ..., hotwork.display_status = ..., etc). Everything
else here is an action-only plain Serializer for a payload that doesn't
round-trip a full model instance (create, dyhod/hod/ood-approve, pause,
complete) -- mirroring crewmanage_drf/inouttag_drf's own split between the
two serializer styles.

HotworkHODChecklistSerializer is the CENTRALIZED "Non Ops requires remarks"
checklist validator (bug-fix item 9): the legacy app copy-pasted this
validation almost verbatim in hod_approve_hotwork (Hotwork/views.py:1205-
1213) and ood_approve_hotwork's night/holiday backfill branch (:1294-1302).
Both HotworkHodApproveSerializer and HotworkOodApproveSerializer subclass it
and call the same `validate_checklist_for_department`/`apply_to_approval`
methods instead of duplicating the rule.
"""

from django.db import transaction
from rest_framework import serializers

from master.models import SubDepartment
from users.models import CustomUserProfile

from .models import AddHotwork, DayType, HotworkHODApproval, HotworkType

NonOps = "Non Ops"


def _profile_summary(profile):
    """Small read-only projection of CustomUserProfile, reused everywhere a
    detail view needs a "rank firstname lastname" style breakdown instead of
    a bare FK id. Returns None when there is no profile so callers never
    need their own null-guard (mirrors inouttag_drf.serializers'
    _profile_summary)."""
    if profile is None:
        return None
    return {
        "id": profile.id,
        "firstname": profile.firstname,
        "lastname": profile.lastname,
        "rank": profile.rank.name if profile.rank_id else None,
        "personal_number": profile.personal_number,
        "department_id": profile.department_id,
        "department": profile.department.name if profile.department_id else None,
    }


def _sub_department_summary(sub_department):
    if sub_department is None:
        return None
    return {
        "id": sub_department.id,
        "name": sub_department.name,
        "department_id": sub_department.department_name_id,
    }


# --------------------------------------------------------------------------
# HotworkHODApproval
# --------------------------------------------------------------------------


class HotworkHODApprovalSerializer(serializers.ModelSerializer):
    department_detail = serializers.SerializerMethodField()
    approved_by_detail = serializers.SerializerMethodField()

    class Meta:
        model = HotworkHODApproval
        fields = (
            "id",
            "hotwork",
            "department",
            "department_detail",
            "approved",
            "approved_by",
            "approved_by_detail",
            "approved_at",
            "earthing_gts",
            "fire_sensor_ops",
            "fire_sensor_non_ops_remarks",
            "flood_sensor_ops",
            "flood_sensor_non_ops_remarks",
            "supply_point",
            "iccp_off",
            "fire_extinguisher",
            "fire_hose",
            "firemain_pressure",
            "free_lagging",
            "sentry_knowledge",
        )
        read_only_fields = fields

    def get_department_detail(self, obj):
        if obj.department_id is None:
            return None
        return {"id": obj.department_id, "name": obj.department.name}

    def get_approved_by_detail(self, obj):
        return _profile_summary(obj.approved_by)


# --------------------------------------------------------------------------
# AddHotwork -- full detail serializer (list/retrieve/pending_approval/
# track/report all share this)
# --------------------------------------------------------------------------


class HotworkSerializer(serializers.ModelSerializer):
    """Full representation of an AddHotwork row. Never used as the *input*
    serializer for create() (see HotworkCreateSerializer below) or for any
    update -- HotworkViewSet only exposes get/post/head/options and every
    write path beyond create() is a dedicated @action, so every field here
    is effectively read-only; read_only_fields spells that out explicitly
    for documentation/safety rather than relying only on the router's
    http_method_names.

    show_actions/display_status/user_already_approved are per-caller,
    per-action computed values the legacy views bolted onto each AddHotwork
    instance in a Python loop (managehotwork's show_actions,
    hotworkapproval's display_status/user_already_approved) -- the view
    methods here set the same attributes on each instance before handing it
    to this serializer, and these SerializerMethodFields just surface
    whatever was set (None/omitted when the current action doesn't compute
    them, e.g. plain retrieve()).
    """

    holiday_or_working_day_display = serializers.CharField(
        source="get_holiday_or_working_day_display", read_only=True
    )
    type_of_hotwork_display = serializers.CharField(
        source="get_type_of_hotwork_display", read_only=True
    )
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True
    )
    current_status = serializers.CharField(read_only=True)

    sub_department_detail = serializers.SerializerMethodField()
    hotwork_incharge_detail = serializers.SerializerMethodField()
    officer_of_the_day_detail = serializers.SerializerMethodField()
    created_by_detail = serializers.SerializerMethodField()
    incharge_approved_by_detail = serializers.SerializerMethodField()
    dyhod_approved_by_detail = serializers.SerializerMethodField()
    ood_approved_by_detail = serializers.SerializerMethodField()
    started_by_detail = serializers.SerializerMethodField()
    paused_by_detail = serializers.SerializerMethodField()
    completed_by_detail = serializers.SerializerMethodField()

    hod_approvals = HotworkHODApprovalSerializer(many=True, read_only=True)

    show_actions = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    user_already_approved = serializers.SerializerMethodField()

    class Meta:
        model = AddHotwork
        fields = (
            "id",
            "hotwork_code",
            "date_of_hotwork",
            "holiday_or_working_day",
            "holiday_or_working_day_display",
            "sub_department",
            "sub_department_detail",
            "sentries_required",
            "previous_hotwork_code",
            "location_of_hotwork",
            "type_of_hotwork",
            "type_of_hotwork_display",
            "departmental_officer",
            "all_adjacent_compartments",
            "sentry_names",
            "hotwork_incharge",
            "hotwork_incharge_detail",
            "dl_number",
            "supervision_welder_name",
            "manager_of_concern_center",
            "officer_of_the_day",
            "officer_of_the_day_detail",
            "remarks",
            "night_work",
            "created_at",
            "created_by",
            "created_by_detail",
            "approval_status",
            "approval_status_display",
            "current_status",
            "incharge_approved",
            "incharge_approved_by",
            "incharge_approved_by_detail",
            "incharge_approved_at",
            "dyhod_approved",
            "dyhod_approved_by",
            "dyhod_approved_by_detail",
            "dyhod_approved_at",
            "all_hods_approved",
            "ood_approved",
            "ood_approved_by",
            "ood_approved_by_detail",
            "ood_approved_at",
            "is_started",
            "started_by",
            "started_by_detail",
            "started_at",
            "is_paused",
            "paused_by",
            "paused_by_detail",
            "paused_at",
            "pause_reason",
            "is_completed",
            "completed_by",
            "completed_by_detail",
            "completed_at",
            "completion_remarks",
            "hod_approvals",
            "show_actions",
            "display_status",
            "user_already_approved",
        )
        read_only_fields = fields

    def get_sub_department_detail(self, obj):
        return _sub_department_summary(obj.sub_department)

    def get_hotwork_incharge_detail(self, obj):
        return _profile_summary(obj.hotwork_incharge)

    def get_officer_of_the_day_detail(self, obj):
        return _profile_summary(obj.officer_of_the_day)

    def get_created_by_detail(self, obj):
        return _profile_summary(obj.created_by)

    def get_incharge_approved_by_detail(self, obj):
        return _profile_summary(obj.incharge_approved_by)

    def get_dyhod_approved_by_detail(self, obj):
        return _profile_summary(obj.dyhod_approved_by)

    def get_ood_approved_by_detail(self, obj):
        return _profile_summary(obj.ood_approved_by)

    def get_started_by_detail(self, obj):
        return _profile_summary(obj.started_by)

    def get_paused_by_detail(self, obj):
        return _profile_summary(obj.paused_by)

    def get_completed_by_detail(self, obj):
        return _profile_summary(obj.completed_by)

    def get_show_actions(self, obj):
        return getattr(obj, "show_actions", None)

    def get_display_status(self, obj):
        return getattr(obj, "display_status", None)

    def get_user_already_approved(self, obj):
        return getattr(obj, "user_already_approved", None)


# --------------------------------------------------------------------------
# Create (addhotwork POST branch, Hotwork/views.py:798-1020)
# --------------------------------------------------------------------------


class HotworkCreateSerializer(serializers.Serializer):
    """Action-only payload for POST hotworks/ (addhotwork's POST branch).
    Reproduces addhotwork's exact required-fields list -- CanCreateHotwork
    (the 'hotwork.create' capability) gates *who* may hit this at the view
    level; this serializer only encodes *what* a valid payload looks like.

    hotwork_incharge is intentionally NOT a field here: the legacy view's
    own assignment of it is fully commented out (Hotwork/views.py:984) --
    new hotworks never set it, though historical rows may still carry one.
    """

    date_of_hotwork = serializers.DateField()
    sub_department = serializers.PrimaryKeyRelatedField(
        queryset=SubDepartment.objects.all(), required=False, allow_null=True
    )
    sentries_required = serializers.BooleanField(required=False, default=True)
    previous_hotwork_code = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    location_of_hotwork = serializers.CharField()
    type_of_hotwork = serializers.ChoiceField(choices=HotworkType)
    departmental_officer = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    all_adjacent_compartments = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    sentry_names = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    dl_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    supervision_welder_name = serializers.CharField()
    manager_of_concern_center = serializers.CharField()
    officer_of_the_day = serializers.PrimaryKeyRelatedField(
        queryset=CustomUserProfile.objects.all()
    )
    remarks = serializers.CharField()
    night_work = serializers.BooleanField(required=False, default=False)
    holiday_or_working_day = serializers.ChoiceField(choices=DayType)

    def create(self, validated_data):
        request = self.context["request"]
        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            raise serializers.ValidationError(
                "User profile not found. Contact administrator."
            )
        night_work = validated_data.get("night_work", False)
        day_type = validated_data.get("holiday_or_working_day")

        # Mirrors addhotwork's initial_status branching exactly
        # (Hotwork/views.py:962-971).
        if night_work or day_type == "holiday":
            initial_status = "pending_ood"
        else:
            initial_status = "pending_dyhod"

        with transaction.atomic():
            # BUG FIX (race condition): legacy generated hotwork_code via
            # `AddHotwork.objects.all().order_by("-created_at").first()`
            # then `int(last.hotwork_code) + 1` with no locking at all
            # (Hotwork/views.py:956-960) -- two concurrent creates could
            # read the same "last" row and both write the same next code.
            # Fixed the same way inouttag_drf.TagOutViewSet.perform_create()
            # fixed the analogous tagout_number race: select_for_update()
            # inside an atomic block serializes concurrent callers.
            last = (
                AddHotwork.objects.select_for_update().order_by("-created_at").first()
            )
            if last and last.hotwork_code and str(last.hotwork_code).isdigit():
                code = int(last.hotwork_code) + 1
            else:
                code = 1

            hotwork = AddHotwork.objects.create(
                date_of_hotwork=validated_data["date_of_hotwork"],
                hotwork_code=str(code),
                sub_department=validated_data.get("sub_department"),
                sentries_required=validated_data.get("sentries_required", True),
                previous_hotwork_code=validated_data.get("previous_hotwork_code")
                or None,
                location_of_hotwork=validated_data["location_of_hotwork"],
                type_of_hotwork=validated_data["type_of_hotwork"],
                departmental_officer=validated_data.get("departmental_officer") or None,
                all_adjacent_compartments=validated_data.get(
                    "all_adjacent_compartments"
                )
                or None,
                sentry_names=validated_data.get("sentry_names") or None,
                dl_number=validated_data.get("dl_number") or None,
                supervision_welder_name=validated_data["supervision_welder_name"],
                manager_of_concern_center=validated_data["manager_of_concern_center"],
                officer_of_the_day=validated_data["officer_of_the_day"],
                remarks=validated_data["remarks"],
                night_work=night_work,
                holiday_or_working_day=day_type,
                created_by=profile,
                approval_status=initial_status,
            )

        return hotwork


# --------------------------------------------------------------------------
# Shared HOD checklist validator (bug-fix item 9 -- CENTRALIZED, used by
# both HotworkHodApproveSerializer and HotworkOodApproveSerializer)
# --------------------------------------------------------------------------


class HotworkHODChecklistSerializer(serializers.Serializer):
    """Shared checklist payload for hod_approve/ood_approve.

    Every field is optional here: only one department's subset is ever
    relevant to a single hod_approve call (resolved from the caller's own
    profile.department_id), while ood_approve's night/holiday backfill
    branch fills all three departments' subsets from ONE shared payload in
    one shot (mirrors ood_approve_hotwork exactly -- the OOD posts one form
    covering all officer checklists at once, Hotwork/views.py:1259-1310).

    New-contract decision (bug-fix item 6, not a "fix" so much as a
    deliberate new naming choice with no existing client to break): field
    names here match the HotworkHODApproval model directly (fire_sensor_ops,
    earthing_gts, ...) instead of the legacy's camelCase POST keys
    (fireSensor, earthingGT, ...).
    """

    earthing_gts = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    fire_sensor_ops = serializers.ChoiceField(
        choices=["Ops", NonOps], required=False, allow_blank=True, default=""
    )
    fire_sensor_non_ops_remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    flood_sensor_ops = serializers.ChoiceField(
        choices=["Ops", NonOps], required=False, allow_blank=True, default=""
    )
    flood_sensor_non_ops_remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    supply_point = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    iccp_off = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    fire_extinguisher = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    fire_hose = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    firemain_pressure = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    free_lagging = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )
    sentry_knowledge = serializers.ChoiceField(
        choices=["Yes", "No"], required=False, allow_blank=True, default=""
    )

    def validate_checklist_for_department(self, attrs, dept_id):
        """CENTRALIZED "Non Ops requires remarks" rule -- ported verbatim
        from hod_approve_hotwork's dept_id==3 branch (Hotwork/
        views.py:1205-1210), and reused UNMODIFIED by
        HotworkOodApproveSerializer's night/holiday backfill validation
        (the legacy app copy-pasted this almost verbatim in both places,
        :1294-1299)."""
        if dept_id == 3:
            if (
                attrs.get("fire_sensor_ops") == NonOps
                and not (attrs.get("fire_sensor_non_ops_remarks") or "").strip()
            ):
                raise serializers.ValidationError(
                    {
                        "fire_sensor_non_ops_remarks": (
                            "Remarks are required when Fire Sensor is Non Ops."
                        )
                    }
                )
            if (
                attrs.get("flood_sensor_ops") == NonOps
                and not (attrs.get("flood_sensor_non_ops_remarks") or "").strip()
            ):
                raise serializers.ValidationError(
                    {
                        "flood_sensor_non_ops_remarks": (
                            "Remarks are required when Flood Sensor is Non Ops."
                        )
                    }
                )
        return attrs

    def apply_to_approval(self, hod_approval, dept_id):
        """Writes only the fields relevant to `dept_id` onto the
        HotworkHODApproval row -- mirrors hod_approve_hotwork's per-
        department field assignment exactly (each department only ever
        touches its own subset, Hotwork/views.py:1194-1219)."""
        data = self.validated_data
        if dept_id == 2:
            hod_approval.earthing_gts = data.get("earthing_gts", "")
        elif dept_id == 3:
            hod_approval.fire_sensor_ops = data.get("fire_sensor_ops", "")
            hod_approval.flood_sensor_ops = data.get("flood_sensor_ops", "")
            hod_approval.supply_point = data.get("supply_point", "")
            hod_approval.iccp_off = data.get("iccp_off", "")
            hod_approval.fire_sensor_non_ops_remarks = (
                data.get("fire_sensor_non_ops_remarks", "")
                if hod_approval.fire_sensor_ops == NonOps
                else ""
            )
            hod_approval.flood_sensor_non_ops_remarks = (
                data.get("flood_sensor_non_ops_remarks", "")
                if hod_approval.flood_sensor_ops == NonOps
                else ""
            )
        elif dept_id == 5:
            hod_approval.fire_extinguisher = data.get("fire_extinguisher", "")
            hod_approval.fire_hose = data.get("fire_hose", "")
            hod_approval.firemain_pressure = data.get("firemain_pressure", "")
            hod_approval.free_lagging = data.get("free_lagging", "")
            hod_approval.sentry_knowledge = data.get("sentry_knowledge", "")


class HotworkDyhodApproveSerializer(serializers.Serializer):
    """Body for hotworks/{id}/dyhod_approve/."""

    action = serializers.ChoiceField(choices=["approve", "reject"])


class HotworkHodApproveSerializer(HotworkHODChecklistSerializer):
    """Body for hotworks/{id}/hod_approve/. `dept_id` is injected into the
    serializer context by the view (the caller's own profile.department_id)
    so the "Non Ops requires remarks" rule only fires for Electrical (3)."""

    action = serializers.ChoiceField(choices=["approve", "reject"])

    def validate(self, attrs):
        if attrs["action"] == "approve":
            dept_id = self.context.get("dept_id")
            attrs = self.validate_checklist_for_department(attrs, dept_id)
        return attrs


class HotworkOodApproveSerializer(HotworkHODChecklistSerializer):
    """Body for hotworks/{id}/ood_approve/. For night/holiday hotworks the
    OOD fills in all 3 departments' checklists in one shot (mirrors
    ood_approve_hotwork exactly) -- the view passes
    context={"apply_checklist": is_night_or_holiday} so the Electrical
    "Non Ops requires remarks" rule is only enforced when that backfill
    branch will actually run, matching the legacy view's validation living
    strictly inside its `if is_night_or_holiday:` block.
    """

    action = serializers.ChoiceField(choices=["approve", "reject"])

    def validate(self, attrs):
        if attrs["action"] == "approve" and self.context.get("apply_checklist"):
            attrs = self.validate_checklist_for_department(attrs, 3)
        return attrs


# --------------------------------------------------------------------------
# Lifecycle actions
# --------------------------------------------------------------------------


class HotworkPauseSerializer(serializers.Serializer):
    """Body for hotworks/{id}/pause/. pause_reason is required -- mirrors
    pause_hotwork's `if not pause_reason: error` (Hotwork/views.py:1383)."""

    pause_reason = serializers.CharField()


class HotworkCompleteSerializer(serializers.Serializer):
    """Body for hotworks/{id}/complete/. completion_remarks is optional
    (may be blank) -- mirrors complete_hotwork exactly, which never
    required it (Hotwork/views.py:1420: `.get('completion_remarks',
    '').strip()`, no presence check)."""

    completion_remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
