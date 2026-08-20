"""
Serializers for crewmanage_drf.

ModelSerializers are used where a viewset maps directly onto a CRUD model
(LeaveApplication, CivilianOfficial, the watch-station master tables). Plain
Serializers are used for action-only payloads that don't round-trip a full
model instance (apply-on-behalf, approve/reject, truncate, date-range
update, personnel-status upsert, sailing create/complete, assignments bulk
save) — mirroring user_drf/serializers.py's split between the two.

The private helpers at the top (_get_profile / _role_name / _log_status_range
/ _delete_status_logs / _absent_pnos) are ports of the same-named module
functions in crewmanage/views.py. They're defined here (not in views.py) so
both this module's .create()/.save() methods and views.py's custom actions
can share one implementation without a circular import (views.py already
imports from serializers.py; the reverse must never happen).
"""

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from users.models import CustomUserProfile

from .models import (
    ActionStationMaster,
    CivilianOfficial,
    CruisingStationMaster,
    DefenceStationMaster,
    EmergencyStationMaster,
    LeaveApplication,
    PersonnelAssignment,
    PersonnelStatusLog,
    Sailing,
    SailingPersonnel,
    SailorRankClassification,
    ShelterStationMaster,
)

TyDuty = "Ty Duty"
EndDateMessage = "End date before start date."
# --------------------------------------------------------------------------
# Shared helpers (ports of crewmanage/views.py module-level functions)
# --------------------------------------------------------------------------


def _get_profile(user):
    """Port of crewmanage/views.py's _get_profile."""
    return (
        CustomUserProfile.objects.filter(id=user.user_profile_id)
        .select_related("rank", "department", "designation_master", "role_master")
        .first()
    )


def _role_name(profile):
    """Port of crewmanage/views.py's _role_name (operates on a profile, not
    a user — distinct from user_drf.permissions' user-based helpers)."""
    if profile and profile.role_master:
        return str(profile.role_master.role_name).strip().lower()
    return ""


def _snapshot_fields(profile):
    """Port of the personnel-snapshot block inside apply_leave_request:
    prefer the FK-linked rank/department/designation_master, falling back to
    the free-text `designation` field."""
    return {
        "rank": profile.rank.name if profile.rank else "",
        "name": f"{profile.firstname} {profile.lastname}".strip(),
        "department": profile.department.name if profile.department else "",
        "designation": (
            profile.designation_master.designation_name
            if profile.designation_master
            else (profile.designation or "")
        ),
    }


def _log_status_range(leave_app):
    """Port of crewmanage/views.py's _log_status_range."""
    current = leave_app.start_date
    while current <= leave_app.end_date:
        PersonnelStatusLog.objects.update_or_create(
            leave_application=leave_app,
            personnel_number=leave_app.personal_number,
            log_date=current,
            defaults={
                "rank": leave_app.rank,
                "name": leave_app.name,
                "department": leave_app.department,
                "designation": leave_app.designation,
                "status": leave_app.leave_type,
            },
        )
        current += timedelta(days=1)


def _delete_status_logs(leave_app):
    """Port of crewmanage/views.py's _delete_status_logs."""
    PersonnelStatusLog.objects.filter(leave_application=leave_app).delete()


def _absent_pnos(start, end):
    """Port of crewmanage/views.py's _absent_pnos."""
    return set(
        LeaveApplication.objects.filter(
            application_status="Approved",
            start_date__lte=end,
            end_date__gte=start,
        ).values_list("personal_number", flat=True)
    )


# --------------------------------------------------------------------------
# Personnel status (get_status_data / get_counts / update_personnel_status)
# --------------------------------------------------------------------------


class PersonnelStatusRowSerializer(serializers.Serializer):
    """Row shape for GET personnel-status/ — serializes the annotated
    `.values()` dicts produced by get_status_data (DRF Serializers support
    plain dict instances via Mapping-based attribute lookup)."""

    id = serializers.IntegerField()
    rank = serializers.CharField(source="rank__name", allow_null=True)
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    personal_number = serializers.CharField()
    department = serializers.CharField(source="department__name", allow_null=True)
    designation = serializers.CharField(
        source="designation_master__designation_name", allow_null=True
    )
    status = serializers.CharField(source="latest_status")


class UpdatePersonnelStatusSerializer(serializers.Serializer):
    """Action-only payload for POST personnel-status/update/ (mirrors
    update_personnel_status). Auth (crew.status.manage, i.e. exactly Head of
    Department) is enforced by the view's permission_classes, not here."""

    personal_number = serializers.CharField()
    rank = serializers.CharField(required=False, allow_blank=True, default="")
    name = serializers.CharField(required=False, allow_blank=True, default="")
    department = serializers.CharField(required=False, allow_blank=True, default="")
    designation = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.CharField()

    def save(self):
        personnel_number = self.validated_data["personal_number"]
        log_date = timezone.now().date()

        existing_log = PersonnelStatusLog.objects.filter(
            personnel_number=personnel_number, log_date=log_date
        ).first()

        if existing_log:
            existing_log.status = self.validated_data["status"]
            existing_log.updated_at = timezone.now()
            existing_log.save()
            return "updated"

        PersonnelStatusLog.objects.create(
            rank=self.validated_data.get("rank", ""),
            name=self.validated_data.get("name", ""),
            personnel_number=personnel_number,
            department=self.validated_data.get("department", ""),
            designation=self.validated_data.get("designation", ""),
            status=self.validated_data["status"],
            log_date=log_date,
        )
        return "inserted"


# --------------------------------------------------------------------------
# Leave applications
# --------------------------------------------------------------------------


class LeaveApplicationSerializer(serializers.ModelSerializer):
    """Full representation of a LeaveApplication — used for list/retrieve
    output and as the create() serializer for POST /leave-applications/
    (apply_leave_request).

    Personnel-snapshot fields (personal_number/rank/name/department/
    designation) are always derived server-side from the caller's own
    profile on create — never accepted from the client — mirroring
    apply_leave_request exactly.
    """

    attachment_url = serializers.SerializerMethodField()
    applied_by_name = serializers.SerializerMethodField()
    approved_rejected_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "personal_number",
            "rank",
            "name",
            "department",
            "designation",
            "leave_type",
            "has_prefix",
            "prefix_start_date",
            "prefix_start_time",
            "start_date",
            "end_date",
            "suffix_completion_date",
            "suffix_completion_time",
            "reporting_date",
            "reporting_time",
            "no_of_days",
            "station",
            "reason",
            "remark",
            "attachment",
            "attachment_url",
            "application_status",
            "rejection_reason",
            "applied_by",
            "applied_by_name",
            "approved_rejected_by",
            "approved_rejected_by_name",
            "approved_rejected_at",
            "applied_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "personal_number",
            "rank",
            "name",
            "department",
            "designation",
            "no_of_days",
            "application_status",
            "rejection_reason",
            "applied_by",
            "approved_rejected_by",
            "approved_rejected_at",
            "applied_at",
            "updated_at",
        )

    def get_attachment_url(self, obj):
        request = self.context.get("request")
        if obj.attachment and request:
            return request.build_absolute_uri(settings.MEDIA_URL + obj.attachment.name)
        return ""

    def get_applied_by_name(self, obj):
        return str(obj.applied_by) if obj.applied_by_id else ""

    def get_approved_rejected_by_name(self, obj):
        return str(obj.approved_rejected_by) if obj.approved_rejected_by_id else ""

    def validate(self, attrs):
        leave_type = attrs.get("leave_type")
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if leave_type not in ("On Leave", TyDuty):
            raise serializers.ValidationError({"leave_type": "Invalid leave type."})
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": EndDateMessage})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        profile = _get_profile(request.user)
        if not profile:
            raise serializers.ValidationError("Profile not found.")

        leave_type = validated_data["leave_type"]
        has_prefix = validated_data.get("has_prefix", False)

        validated_data.update(_snapshot_fields(profile))
        if not has_prefix:
            validated_data["prefix_start_date"] = None
        if not (has_prefix and leave_type == TyDuty):
            validated_data["prefix_start_time"] = None
        if leave_type != TyDuty:
            validated_data["suffix_completion_time"] = None
            validated_data["reporting_time"] = None
        validated_data["application_status"] = "Pending"
        validated_data["applied_by"] = profile

        return super().create(validated_data)


class LeaveDatesUpdateSerializer(serializers.Serializer):
    """Action-only payload for PATCH /leave-applications/{id}/
    (update_leave_dates). Legacy only ever touched start_date/end_date via
    this endpoint — not a general partial update of every field — so this
    is a dedicated Serializer rather than routing through
    LeaveApplicationSerializer's partial-update path."""

    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": EndDateMessage})
        return attrs

    def save(self, leave_application):
        _delete_status_logs(leave_application)
        leave_application.start_date = self.validated_data["start_date"]
        leave_application.end_date = self.validated_data["end_date"]
        leave_application.save()  # model.save() recomputes no_of_days
        _log_status_range(leave_application)
        return leave_application


class TruncateLeaveSerializer(serializers.Serializer):
    """Action-only payload for POST /leave-applications/{id}/truncate/
    (truncate_leave). personal_number/application_id are no longer needed
    as inputs — both are already known from the resolved instance/URL pk."""

    new_end_date = serializers.DateField()

    def save(self, leave_application):
        new_end = self.validated_data["new_end_date"]

        if new_end < leave_application.start_date:
            leave_application.application_status = "Rejected"
            leave_application.end_date = leave_application.start_date
        else:
            leave_application.end_date = new_end
        leave_application.save()  # recomputes no_of_days

        # Matches legacy exactly: the log-deletion cutoff is the *requested*
        # new_end_date, not necessarily the final saved end_date (those
        # differ when new_end < start_date).
        PersonnelStatusLog.objects.filter(
            personnel_number=leave_application.personal_number,
            log_date__gt=new_end,
        ).delete()
        return leave_application


class ApplyOnBehalfSerializer(serializers.Serializer):
    """Action-only payload for POST /leave-applications/apply_on_behalf/
    (hod_apply_leave_for_personnel — the ACTIVE definition at
    crewmanage/views.py:1524; the fully-commented-out dead copy around
    lines 230-331 is ignored). Capability gating ('crew.leave.apply_on_behalf')
    is enforced by the view, not here."""

    personal_number = serializers.CharField()
    leave_type = serializers.ChoiceField(choices=["On Leave", TyDuty])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    has_prefix = serializers.BooleanField(required=False, default=False)
    prefix_start_date = serializers.DateField(required=False, allow_null=True)
    prefix_start_time = serializers.TimeField(required=False, allow_null=True)
    suffix_completion_date = serializers.DateField(required=False, allow_null=True)
    suffix_completion_time = serializers.TimeField(required=False, allow_null=True)
    reporting_date = serializers.DateField(required=False, allow_null=True)
    reporting_time = serializers.TimeField(required=False, allow_null=True)
    station = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    remark = serializers.CharField(required=False, allow_blank=True, default="")
    attachment = serializers.FileField(required=False, allow_null=True)
    # Fallback overrides used only when the target profile itself has no
    # rank/department/designation set — mirrors the
    # `request.POST.get(...)` fallback chain in hod_apply_leave_for_personnel.
    rank = serializers.CharField(required=False, allow_blank=True, default="")
    department = serializers.CharField(required=False, allow_blank=True, default="")
    designation = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": EndDateMessage})
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        applier_profile = _get_profile(request.user)

        target = (
            CustomUserProfile.objects.select_related(
                "rank", "department", "designation_master"
            )
            .filter(personal_number=validated_data["personal_number"])
            .first()
        )
        if not target:
            raise serializers.ValidationError(
                {
                    "personal_number": (
                        f"Personnel {validated_data['personal_number']} not found"
                    )
                }
            )

        leave_type = validated_data["leave_type"]
        has_prefix = validated_data.get("has_prefix", False)

        rank = target.rank.name if target.rank else validated_data.get("rank", "")
        department = (
            target.department.name
            if target.department
            else validated_data.get("department", "")
        )
        designation = (
            target.designation_master.designation_name
            if target.designation_master
            else (target.designation or validated_data.get("designation", ""))
        )

        leave_app = LeaveApplication.objects.create(
            personal_number=target.personal_number,
            rank=rank,
            name=f"{target.firstname} {target.lastname}".strip(),
            department=department,
            designation=designation,
            leave_type=leave_type,
            has_prefix=has_prefix,
            prefix_start_date=(
                validated_data.get("prefix_start_date") if has_prefix else None
            ),
            prefix_start_time=(
                validated_data.get("prefix_start_time")
                if has_prefix and leave_type == TyDuty
                else None
            ),
            start_date=validated_data["start_date"],
            end_date=validated_data["end_date"],
            suffix_completion_date=validated_data.get("suffix_completion_date"),
            suffix_completion_time=(
                validated_data.get("suffix_completion_time")
                if leave_type == TyDuty
                else None
            ),
            reporting_date=validated_data.get("reporting_date"),
            reporting_time=(
                validated_data.get("reporting_time") if leave_type == TyDuty else None
            ),
            station=validated_data.get("station", ""),
            reason=validated_data.get("reason", ""),
            remark=validated_data.get("remark", ""),
            attachment=validated_data.get("attachment"),
            application_status="Approved",
            approved_rejected_by=applier_profile,
            approved_rejected_at=timezone.now(),
            applied_by=applier_profile,
        )
        _log_status_range(leave_app)
        return leave_app


# --------------------------------------------------------------------------
# Watch Station Bill — civilians
# --------------------------------------------------------------------------


class CivilianOfficialSerializer(serializers.ModelSerializer):
    class Meta:
        model = CivilianOfficial
        fields = (
            "id",
            "name_snapshot",
            "role",
            "ref_id",
            "contact",
            "remarks",
            "is_active",
            "person_type",
            "rank_snapshot",
            "pno_snapshot",
            "dept_snapshot",
            "desig_snapshot",
            "service_no",
            "fleet",
            "ship",
            "cid",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_active", "created_by", "created_at", "updated_at")

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        # Matches watch_station_bill_civilian_add exactly: pno_snapshot is
        # always set equal to service_no on add, regardless of anything the
        # client sent for pno_snapshot.
        validated_data["pno_snapshot"] = validated_data.get("service_no", "")
        return super().create(validated_data)


# --------------------------------------------------------------------------
# Watch Station Bill — sailings
# --------------------------------------------------------------------------


class SailingListSerializer(serializers.ModelSerializer):
    """Row shape for GET sailings/ (watch_station_bill_sailings_list)."""

    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    co = serializers.CharField(source="co_name", read_only=True)
    xo = serializers.CharField(source="xo_name", read_only=True)
    completed_at = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    personnel_count = serializers.SerializerMethodField()

    class Meta:
        model = Sailing
        fields = (
            "id",
            "name",
            "area",
            "start",
            "end",
            "co",
            "xo",
            "remarks",
            "status",
            "completed_at",
            "created_at",
            "personnel_count",
        )

    def get_start(self, obj):
        return str(obj.start_date) if obj.start_date else ""

    def get_end(self, obj):
        return str(obj.end_date) if obj.end_date else ""

    def get_completed_at(self, obj):
        return str(obj.completed_at) if obj.completed_at else ""

    def get_created_at(self, obj):
        return str(obj.created_at.date()) if obj.created_at else ""

    def get_personnel_count(self, obj):
        return obj.personnel.count()


class SailingCreateSerializer(serializers.Serializer):
    """Action-only payload for POST sailings/ — the FINAL/ACTIVE
    _sailing_create definition at crewmanage/views.py:2495 (two earlier
    dead/commented copies of this name are ignored). Handles the "Fill Same
    Strength As" copy_from_sailing_id deep-copy feature."""

    name = serializers.CharField()
    area = serializers.CharField(required=False, allow_blank=True, default="")
    start = serializers.CharField()  # "YYYY-MM-DD"
    start_time = serializers.CharField()  # "HH:MM"
    co = serializers.CharField(required=False, allow_blank=True, default="")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    copy_from_sailing_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        try:
            start_dt = datetime.strptime(
                f"{attrs['start']} {attrs['start_time']}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            raise serializers.ValidationError("Invalid departure date/time.")
        attrs["start_datetime"] = (
            timezone.make_aware(start_dt) if settings.USE_TZ else start_dt
        )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        sailing = Sailing.objects.create(
            name=validated_data["name"].strip(),
            area=validated_data.get("area", "").strip(),
            start_date=validated_data["start_datetime"],
            end_date=None,
            co_name=validated_data.get("co", "").strip(),
            xo_name="",
            remarks=validated_data.get("remarks", "").strip(),
            created_by=request.user,
            status="active",
        )

        copied_personnel = 0
        copied_assignments = 0
        copy_from_id = validated_data.get("copy_from_sailing_id")
        if copy_from_id:
            src = Sailing.objects.filter(pk=copy_from_id).first()
            if src:
                for sp in src.personnel.all():
                    SailingPersonnel.objects.create(
                        sailing=sailing,
                        profile=sp.profile,
                        rank_snapshot=sp.rank_snapshot,
                        name_snapshot=sp.name_snapshot,
                        pno_snapshot=sp.pno_snapshot,
                        dept_snapshot=sp.dept_snapshot,
                        desig_snapshot=sp.desig_snapshot,
                        person_type=sp.person_type,
                        role=sp.role,
                        service_no=sp.service_no,
                        fleet=sp.fleet,
                        ship=sp.ship,
                        cid=sp.cid,
                        contact=sp.contact,
                        remarks=sp.remarks,
                        watch_station=sp.watch_station,
                        action_station=sp.action_station,
                        status_override=sp.status_override,
                        created_by=request.user.CustomUser_profile,
                    )
                    copied_personnel += 1

                for a in src.assignments.all():
                    PersonnelAssignment.objects.create(
                        sailing=sailing,
                        pno=a.pno,
                        name_snapshot=a.name_snapshot,
                        rank_snapshot=a.rank_snapshot,
                        dept_snapshot=a.dept_snapshot,
                        w3=a.w3,
                        w2=a.w2,
                        action=a.action,
                        defence=a.defence,
                        cruising=a.cruising,
                        shelter=a.shelter,
                        emergency=a.emergency,
                        lr=a.lr,
                        mess=a.mess,
                        ssd=a.ssd,
                        mess_stn=a.mess_stn,
                        section=a.section,
                        remarks=a.remarks,
                        blood_group=a.blood_group,
                    )
                    copied_assignments += 1

        sailing.copied_personnel = copied_personnel
        sailing.copied_assignments = copied_assignments
        return sailing


class SailingCompleteSerializer(serializers.Serializer):
    """Action-only payload for POST sailings/{id}/complete/
    (watch_station_bill_sailing_complete)."""

    completed_date = serializers.CharField(required=False, allow_blank=True)
    completed_time = serializers.CharField(
        required=False, allow_blank=True, default="00:00"
    )

    def validate(self, attrs):
        comp_date_raw = attrs.get("completed_date") or str(timezone.localdate())
        comp_time_raw = attrs.get("completed_time") or "00:00"
        try:
            comp_dt = datetime.strptime(
                f"{comp_date_raw} {comp_time_raw}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            raise serializers.ValidationError("Invalid date/time")
        attrs["completed_datetime"] = comp_dt
        return attrs

    def save(self, sailing):
        comp_dt = self.validated_data["completed_datetime"]
        if settings.USE_TZ:
            comp_dt = timezone.make_aware(comp_dt)
        sailing.end_date = comp_dt
        sailing.status = "completed"
        sailing.save()
        return sailing


class AssignmentsSaveSerializer(serializers.Serializer):
    """Action-only payload for POST sailings/{id}/assignments/ — bulk upsert
    from a `rows` array (watch_station_bill_assignments_save)."""

    rows = serializers.ListField(child=serializers.DictField(), required=False)

    def save(self, sailing):
        rows = self.validated_data.get("rows") or []
        sp_lookup = {sp.pno_snapshot: sp for sp in sailing.personnel.all()}

        updated = 0
        for row in rows:
            pno = str(row.get("pno", "")).strip()
            if not pno:
                continue
            sp = sp_lookup.get(pno)
            PersonnelAssignment.objects.update_or_create(
                sailing=sailing,
                pno=pno,
                defaults={
                    "name_snapshot": sp.name_snapshot if sp else row.get("name", ""),
                    "rank_snapshot": sp.rank_snapshot if sp else row.get("rank", ""),
                    "dept_snapshot": (
                        sp.dept_snapshot if sp else row.get("dept", "Unknown")
                    ),
                    "w3": row.get("w3", ""),
                    "w2": row.get("w2", ""),
                    "action": row.get("action", ""),
                    "defence": row.get("defence", ""),
                    "cruising": row.get("cruising", ""),
                    "shelter": row.get("shelter", ""),
                    "emergency": row.get("emergency", ""),
                    "lr": row.get("lr", ""),
                    "mess": row.get("mess", ""),
                    "ssd": row.get("ssd", ""),
                    "mess_stn": row.get("mess_stn", ""),
                    "section": row.get("section", ""),
                    "remarks": row.get("remarks", ""),
                    "blood_group": row.get("blood_group", ""),
                },
            )
            updated += 1
        return updated


# --------------------------------------------------------------------------
# Watch Station Bill — masters (Action/Defence/Cruising/Shelter/Emergency
# Station + Junior/Senior Sailor Classification). 6 idiomatic ModelViewSets
# replace the legacy MASTER_MODEL_MAP string-dispatch (watchbill_masters_
# list/add/update/delete); same underlying CRUD, no string-dispatch needed.
# --------------------------------------------------------------------------


class _UniqueNameMasterSerializer(serializers.ModelSerializer):
    """Shared uniqueness check (mirrors watchbill_masters_add/update's
    case-insensitive "this entry already exists" validation) for the 5
    plain name-only master tables."""

    def validate_name(self, value):
        value = value.strip()
        model = self.Meta.model
        qs = model.objects.filter(name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This entry already exists.")
        return value


class ActionStationMasterSerializer(_UniqueNameMasterSerializer):
    class Meta:
        model = ActionStationMaster
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class DefenceStationMasterSerializer(_UniqueNameMasterSerializer):
    class Meta:
        model = DefenceStationMaster
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CruisingStationMasterSerializer(_UniqueNameMasterSerializer):
    class Meta:
        model = CruisingStationMaster
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ShelterStationMasterSerializer(_UniqueNameMasterSerializer):
    class Meta:
        model = ShelterStationMaster
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class EmergencyStationMasterSerializer(_UniqueNameMasterSerializer):
    class Meta:
        model = EmergencyStationMaster
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class SailorRankClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SailorRankClassification
        fields = ("id", "rank_name", "classification", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_rank_name(self, value):
        value = value.strip()
        qs = SailorRankClassification.objects.filter(rank_name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This rank is already classified.")
        return value
