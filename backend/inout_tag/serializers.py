from rest_framework import serializers

from master.models import Department
from sfd.models import ShipEquipment

from .models import (
    ConditionChoices,
    TagIn,
    TagInApproval,
    TagOut,
    TagOutReasonChoices,
    TypeChoices,
)

DATEFORMAT = "%d %b %Y"


def _profile_summary(profile):
    """Small read-only projection of CustomUserProfile, reused everywhere a
    legacy view hand-built a "rank firstname lastname" string or a
    department/ship name. Returns None when there is no profile, so callers
    never need their own null-guard."""
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
        "ship_id": profile.ship_id,
        "ship": profile.ship.name if profile.ship_id else None,
        "role": profile.role_master.role_name if profile.role_master_id else None,
    }


# --------------------------------------------------------------------------
# TagOut
# --------------------------------------------------------------------------


class TagOutSerializer(serializers.ModelSerializer):
    """Replaces the hand-built dict in get_tagout_details -- every key that
    dict returned is present here, either as the raw model field, a
    `..._display` (get_..._display()) field, or a `..._detail` nested/joined
    field. `date`/`expected_date_of_tagin`/`estimated_bom_arrival_date`/
    `approved_on` additionally get a formatted `..._display` twin matching
    the legacy strftime formats, alongside the raw ISO value (kept for
    sorting/editing on the frontend).

    Fields the legacy `addtagout` view validated as "required" even though
    the model itself allows blank/null are re-declared here with
    required=True, so create() rejects incomplete payloads the same way the
    legacy view's own `required_fields` list did.
    """

    date = serializers.DateField(required=True)
    tagout_equipment_name = serializers.PrimaryKeyRelatedField(
        queryset=ShipEquipment.objects.all(), required=True
    )
    expected_date_of_tagin = serializers.DateField(required=True)
    name_of_subsystem = serializers.CharField(required=True)
    type = serializers.ChoiceField(choices=TypeChoices, required=True)
    tagout_maintainer_name_rank = serializers.CharField(required=True)
    name_of_component = serializers.CharField(required=True)
    condition = serializers.ChoiceField(choices=ConditionChoices, required=True)
    serial_number_of_component = serializers.CharField(required=True)
    weight_of_component = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=True
    )
    tagout_reason = serializers.ChoiceField(choices=TagOutReasonChoices, required=True)
    tagout_description = serializers.CharField(required=True)

    departments_affected = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(active=1), many=True, required=False
    )

    user_profile_detail = serializers.SerializerMethodField()
    created_by_detail = serializers.SerializerMethodField()
    approved_by_detail = serializers.SerializerMethodField()
    tagout_equipment_name_detail = serializers.SerializerMethodField()
    departments_affected_detail = serializers.SerializerMethodField()

    type_display = serializers.CharField(source="get_type_display", read_only=True)
    condition_display = serializers.CharField(
        source="get_condition_display", read_only=True
    )
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True
    )
    tagout_reason_display = serializers.CharField(
        source="get_tagout_reason_display", read_only=True
    )

    date_display = serializers.SerializerMethodField()
    expected_date_of_tagin_display = serializers.SerializerMethodField()
    estimated_bom_arrival_date_display = serializers.SerializerMethodField()
    approved_on_display = serializers.SerializerMethodField()
    has_tagin = serializers.SerializerMethodField()

    class Meta:
        model = TagOut
        fields = (
            "id",
            "tagout_number",
            "date",
            "date_display",
            "user_profile",
            "user_profile_detail",
            "tagout_equipment_name",
            "tagout_equipment_name_detail",
            "name_of_subsystem",
            "name_of_component",
            "serial_number_of_component",
            "pattern_number_of_component",
            "weight_of_component",
            "type",
            "type_display",
            "condition",
            "condition_display",
            "special_instructions",
            "departments_affected",
            "departments_affected_detail",
            "expected_date_of_tagin",
            "expected_date_of_tagin_display",
            "tagout_reason",
            "tagout_reason_display",
            "tagout_description",
            "tagout_maintainer_name_rank",
            "ty_loan_ship",
            "ty_authority",
            "ty_item_taken_by",
            "ty_additional_items",
            "survery_demand_authority",
            "repair_ra_number",
            "repair_landed_details",
            "repair_item_taken_by",
            "repair_additional_items",
            "aber_authority",
            "replacement_item",
            "estimated_bom_arrival_date",
            "estimated_bom_arrival_date_display",
            "approval_status",
            "approval_status_display",
            "approved_by",
            "approved_by_detail",
            "approved_on",
            "approved_on_display",
            "created_on",
            "created_by",
            "created_by_detail",
            "modified_on",
            "active",
            "has_tagin",
        )
        read_only_fields = (
            "id",
            "tagout_number",
            "user_profile",
            "approval_status",
            "approved_by",
            "approved_on",
            "created_on",
            "created_by",
            "modified_on",
            "active",
        )

    def get_user_profile_detail(self, obj):
        return _profile_summary(obj.user_profile)

    def get_created_by_detail(self, obj):
        return _profile_summary(obj.created_by)

    def get_approved_by_detail(self, obj):
        return _profile_summary(obj.approved_by)

    def get_tagout_equipment_name_detail(self, obj):
        equipment = obj.tagout_equipment_name
        if equipment is None:
            return None
        return {"id": equipment.id, "nomenclature": equipment.nomenclature}

    def get_departments_affected_detail(self, obj):
        return [{"id": d.id, "name": d.name} for d in obj.departments_affected.all()]

    def get_date_display(self, obj):
        return obj.date.strftime(DATEFORMAT) if obj.date else None

    def get_expected_date_of_tagin_display(self, obj):
        return (
            obj.expected_date_of_tagin.strftime(DATEFORMAT)
            if obj.expected_date_of_tagin
            else None
        )

    def get_estimated_bom_arrival_date_display(self, obj):
        return (
            obj.estimated_bom_arrival_date.strftime(DATEFORMAT)
            if obj.estimated_bom_arrival_date
            else None
        )

    def get_approved_on_display(self, obj):
        return (
            obj.approved_on.strftime("%d %b %Y, %I:%M %p") if obj.approved_on else None
        )

    def get_has_tagin(self, obj):
        return hasattr(obj, "tagin")


class TagOutApprovalActionSerializer(serializers.Serializer):
    """Body for `tagouts/{id}/approve/`."""

    action = serializers.ChoiceField(choices=["approve", "reject"])


# --------------------------------------------------------------------------
# TagIn / TagInApproval
# --------------------------------------------------------------------------


class TagInApprovalSerializer(serializers.ModelSerializer):
    department_detail = serializers.SerializerMethodField()
    approved_by_detail = serializers.SerializerMethodField()
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True
    )

    class Meta:
        model = TagInApproval
        fields = (
            "id",
            "tagin",
            "department",
            "department_detail",
            "approval_status",
            "approval_status_display",
            "approved_by",
            "approved_by_detail",
            "approved_on",
            "remarks",
            "created_on",
            "active",
        )
        read_only_fields = fields

    def get_department_detail(self, obj):
        if obj.department_id is None:
            return None
        return {"id": obj.department_id, "name": obj.department.name}

    def get_approved_by_detail(self, obj):
        return _profile_summary(obj.approved_by)


class TagInSerializer(serializers.ModelSerializer):
    """Replaces the hand-built dict in get_tagin_details. `tagout_detail`
    nests the full TagOutSerializer (every reason-specific field the legacy
    dict flattened onto the tagin payload lives there instead), and
    `approval_list` replaces the `tagin.approval_list = ...` attribute the
    legacy `tag_in` view bolted onto each row in a Python loop.

    `tagin_maintainer_name_rank`, `tagin_remarks`, and `status` are
    read-only: the legacy `add_tagin` view always derived them itself
    (`tagin_maintainer_name_rank = tagin_maintainer`, `tagin_remarks =
    tagin_description`, `status = 'completed'`) rather than accepting them
    as independent input, so that derivation is reproduced in
    TagInViewSet.perform_create instead of exposing them as writable here.
    """

    tagout_detail = TagOutSerializer(source="tagout", read_only=True)
    created_by_detail = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    approval_status_display = serializers.CharField(
        source="get_approval_status_display", read_only=True
    )
    tagin_date_display = serializers.SerializerMethodField()
    approval_list = serializers.SerializerMethodField()

    class Meta:
        model = TagIn
        fields = (
            "id",
            "tagout",
            "tagout_detail",
            "tagin_date",
            "tagin_date_display",
            "tagin_description",
            "tagin_maintainer",
            "tagin_maintainer_name_rank",
            "all_items_returned",
            "items_pending",
            "status",
            "status_display",
            "approval_status",
            "approval_status_display",
            "tagin_remarks",
            "created_on",
            "created_by",
            "created_by_detail",
            "active",
            "approval_list",
        )
        read_only_fields = (
            "id",
            "tagin_maintainer_name_rank",
            "status",
            "approval_status",
            "tagin_remarks",
            "created_on",
            "created_by",
            "active",
        )

    def get_created_by_detail(self, obj):
        return _profile_summary(obj.created_by)

    def get_tagin_date_display(self, obj):
        return obj.tagin_date.strftime(DATEFORMAT) if obj.tagin_date else None

    def get_approval_list(self, obj):
        return TagInApprovalSerializer(
            obj.tagin_approvals.filter(active=1), many=True
        ).data

    def validate_tagout(self, value):
        """Mirrors `add_tagin`'s `TagOut.objects.get(id=..., active=1,
        approval_status='approved')` fetch and its OneToOne "already has a
        TagIn" guard."""
        if value.active != 1 or value.approval_status != "approved":
            raise serializers.ValidationError("TagOut not found or not approved.")
        if hasattr(value, "tagin"):
            raise serializers.ValidationError(
                f"Tag In already exists for {value.tagout_number}."
            )
        return value

    def validate(self, attrs):
        """Mirrors add_tagin's "all items returned XOR items pending" rule."""
        all_items_returned = attrs.get(
            "all_items_returned",
            getattr(self.instance, "all_items_returned", True),
        )
        items_pending = attrs.get(
            "items_pending", getattr(self.instance, "items_pending", "") or ""
        )
        if not all_items_returned and not items_pending.strip():
            raise serializers.ValidationError(
                {
                    "items_pending": (
                        'Please either check "All items returned back" or '
                        'provide details in "Items Pending" field.'
                    )
                }
            )
        return attrs


class TagInApprovalActionSerializer(serializers.Serializer):
    """Body for `tagins/{id}/approve/`."""

    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HistorySerializer(serializers.ModelSerializer):
    ship_name = serializers.CharField(
        source="user_profile.ship.name",
        read_only=True,
    )
    department_name = serializers.CharField(
        source="user_profile.department.name",
        read_only=True,
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name",
        read_only=True,
    )
    departments_affected = serializers.SerializerMethodField()

    class Meta:
        model = TagOut
        fields = (
            "id",
            "date",
            "ship_name",
            "department_name",
            "created_by_name",
            "departments_affected",
            "active",
        )

    def get_departments_affected(self, obj):
        return [
            {
                "id": department.id,
                "name": department.name,
            }
            for department in obj.departments_affected.all()
        ]
