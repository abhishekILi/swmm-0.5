from rest_framework import serializers

from .models import (
    CoMessage,
    HierarchyForChart,
    MemberDetail,
    OrderDuty,
    Quote,
    Ship,
    ShipRole,
    ShipRoleImage,
    UpdateEntry,
)


class UpdateEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = UpdateEntry
        fields = (
            "id",
            "uploaded_date",
            "from_date",
            "to_date",
            "update_text",
            "event_file",
        )
        read_only_fields = ("uploaded_date",)


class ShipRoleImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipRoleImage
        fields = (
            "id",
            "image",
        )


class ShipRoleSerializer(serializers.ModelSerializer):
    images = ShipRoleImageSerializer(many=True, read_only=True)

    class Meta:
        model = ShipRole
        fields = (
            "id",
            "role_title",
            "current_text",
            "uploaded_date",
            "images",
        )
        read_only_fields = ("uploaded_date",)


class MemberDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberDetail
        fields = (
            "id",
            "name",
            "designation",
            "rank",
            "image_path",
            "uploaded_date",
        )
        read_only_fields = ("uploaded_date",)


class OrderDutySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDuty
        fields = (
            "id",
            "filename",
            "uploaded_at",
            "source",
            "pdf_path",
            "roster_name",
            "from_date",
            "to_date",
            "description",
            "date",
            "officer_details",
            "routine_details",
            "batch_id",
            "allocation_type",
        )
        read_only_fields = ("uploaded_at",)


class QuoteSerializer(serializers.ModelSerializer):
    quoteText = serializers.CharField(source="quote_text", read_only=True)
    addedDate = serializers.DateTimeField(
        source="uploaded_date",
        format="%Y-%m-%d",
        read_only=True,
    )

    class Meta:
        model = Quote
        fields = (
            "id",
            "quote_text",
            "quoteText",
            "uploaded_date",
            "addedDate",
            "is_active",
            "is_displayed",
            "last_displayed_date",
        )
        read_only_fields = (
            "uploaded_date",
            "addedDate",
        )


class CoMessageSerializer(serializers.ModelSerializer):
    uploaded_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = CoMessage
        fields = (
            "id",
            "message",
            "valid_till_date",
            "uploaded_date",
        )
        read_only_fields = ("uploaded_date",)


class HierarchyForChartSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="user.first_name",
        read_only=True,
    )
    last_name = serializers.CharField(
        source="user.last_name",
        read_only=True,
    )
    designation = serializers.CharField(
        source="user.designation",
        read_only=True,
    )
    personnel_number = serializers.CharField(
        source="user.personnel_number",
        read_only=True,
    )
    mobile_number = serializers.CharField(
        source="user.mobile_number",
        read_only=True,
    )
    nud_mail = serializers.EmailField(
        source="user.nud_mail",
        read_only=True,
    )
    rank = serializers.CharField(read_only=True)

    class Meta:
        model = HierarchyForChart
        fields = (
            "id",
            "node_type",
            "division_name",
            "user",
            "photo",
            "is_regulator",
            "parent",
            "is_commander_officer",
            "date",
            "assigned_regulator",
            # User details
            "first_name",
            "last_name",
            "designation",
            "personnel_number",
            "mobile_number",
            "nud_mail",
            "rank",
        )


class ShipKnowYourShipSerializer(serializers.ModelSerializer):
    ship_category = serializers.CharField(
        source="ship_category_string",
        read_only=True,
    )
    class_name = serializers.CharField(
        source="class_master_string",
        read_only=True,
    )
    command_name = serializers.CharField(
        source="command_string",
        read_only=True,
    )
    authority_name = serializers.CharField(
        source="authority_string",
        read_only=True,
    )
    propulsion_name = serializers.CharField(
        source="propulsion_string",
        read_only=True,
    )

    ship_image = serializers.SerializerMethodField()
    specifications = serializers.SerializerMethodField()

    class Meta:
        model = Ship
        exclude = (
            "universal_id_m_ship",
            "universal_id_m_ship_category",
            "universal_id_m_ship_class",
            "universal_id_m_command",
            "universal_id_m_ops_authority",
            "universal_id_m_propulsion",
            "universal_id_a_user_created_by",
            "universal_id_a_user_updated_by",
            "universal_id_m_overseeing_team",
            "universal_id_m_ship_unit_category",
        )

    def get_ship_image(self, obj) -> str | None:
        request = self.context.get("request")

        if not obj.ship_image:
            return None

        return request.build_absolute_uri(obj.ship_image.url)

    def get_specifications(self, obj) -> list[dict]:
        return [
            {
                "label": "Length",
                "value": f"{obj.length_overall} Meters" if obj.length_overall else None,
                "icon": "Ship",
                "theme": "blue",
            },
            {
                "label": "Crew Capacity",
                "value": (
                    f"{obj.overseeing_team_string} Personnel"
                    if obj.overseeing_team_string
                    else None
                ),
                "icon": "Box",
                "theme": "purple",
            },
            {
                "label": "Operational",
                "value": (
                    f"{obj.distance_run} Nautical Miles" if obj.distance_run else None
                ),
                "icon": "Anchor",
                "theme": "pink",
            },
            {
                "label": "Top Speed",
                "value": (
                    f"{obj.max_cont_speed} Knots" if obj.max_cont_speed else None
                ),
                "icon": "Navigation",
                "theme": "cyan",
            },
            {
                "label": "Type",
                "value": (
                    obj.ship_category.ship_category_name if obj.ship_category else None
                ),
                "icon": "Anchor",
                "theme": "pink",
            },
            {
                "label": "Length",
                "value": obj.length_perpen if obj.length_perpen else None,
                "icon": "Ship",
                "theme": "blue",
            },
        ]


# ─────────────────────────────────────────────────────────────
# CMMS Refit Integration Serializers
# ─────────────────────────────────────────────────────────────


class GenericSuccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.JSONField(required=False, default=None, allow_null=True)


class MaintenanceNomenclatureSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    type = serializers.ChoiceField(choices=("OPERATIONAL", "REFIT"))
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    maintenance_period = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    occasion = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class MaintenanceNomenclatureResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    maint_nomenclature = MaintenanceNomenclatureSerializer(many=True)


class MaintenanceNomenclatureDeleteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=("OPERATIONAL", "REFIT"))


class RefitCompletionCreateSerializer(serializers.Serializer):
    ship_code = serializers.CharField(required=True)
    refit_type = serializers.CharField(required=True)
    planned_start_date = serializers.DateField(required=True)
    planned_end_date = serializers.DateField(required=True)
    actual_start_date = serializers.DateField(required=False, allow_null=True)
    actual_end_date = serializers.DateField(required=False, allow_null=True)
    refit_place = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    universal_id_m_command = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class RefitCompletionResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    Universal_ID_T_RefComp = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class RefitDelinquencyCreateSerializer(serializers.Serializer):
    delinquency_code = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    days_delayed = serializers.IntegerField(required=True)
    remarks = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class RefitDryDockingCreateSerializer(serializers.Serializer):
    dock_entry_date = serializers.DateField(required=True)
    dock_undock_date = serializers.DateField(required=True)
    yard_dock_name = serializers.CharField(required=True)
    hull_inspection_status = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class RefitOCRCreateSerializer(serializers.Serializer):
    report_ref_no = serializers.CharField(required=True)
    clearance_status = serializers.CharField(required=True)
    trial_outcome = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    report_date = serializers.DateField(required=True)


class RefitSyncPayloadResponseSerializer(serializers.Serializer):
    M_Delinquery = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_RefComDelinquery_Detail = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_Refit = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_DryDocking = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    M_OCR = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
    T_Refcomp = serializers.ListField(
        child=serializers.DictField(), required=False, default=[]
    )
