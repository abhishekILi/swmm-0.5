from rest_framework import serializers

from dart.models import InitiateDart
from master.models import Ship

from .models import (
    Authority,
    Demand,
    Denomination,
    EquipmentClass,
    Issue,
    IssueList,
    NotInCattedItem,
    PlannedRoutineSpareList,
    PostDemand,
    PostReceive,
    PostSurvey,
    Receive,
    Return,
    RoutineSpareUsage,
    SpareClass,
    Spares,
    SparesMapping,
    Survey,
)


class UppercaseFieldsSerializerMixin:
    def to_internal_value(self, data):
        data = data.copy()
        uppercase_fields = getattr(self.Meta.model, "uppercase_fields", ())
        for field_name in uppercase_fields:
            value = data.get(field_name)
            if isinstance(value, str):
                data[field_name] = value.upper()
        return super().to_internal_value(data)


class SpareClassSerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = SpareClass
        fields = ("id", "name", "department")


class EquipmentClassSerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = EquipmentClass
        fields = ("id", "name", "spare_class")


class DenominationSerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = Denomination
        fields = ("id", "name", "department")


class AuthoritySerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = Authority
        fields = ("id", "name")


class SparesSerializer(UppercaseFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Spares
        fields = (
            "id",
            "equipment_class",
            "pattern_number",
            "description",
            "category",
            "critical",
            "compartment",
            "location",
            "rack_position",
            "rack_number",
            "denomination",
            "quantity_authorised",
            "quantity_available",
            "authority",
            "page",
            "line",
            "remarks",
            "mo_demand_number",
            "image",
            "is_obs",
        )


class RoutineSpareUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutineSpareUsage
        fields = (
            "id",
            "routine",
            "routine_description",
            "spare",
            "quantity_used",
            "date_used",
        )


class IssueSerializer(UppercaseFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = (
            "id",
            "spare",
            "equipment",
            "date_of_issue",
            "username",
            "quantity_issued",
            "issue_time",
            "remarks",
            "dart_number",
        )


class IssueListSerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = IssueList
        fields = ("id", "issue_entry", "quantity_toreturn", "dart_number")


class ReturnSerializer(UppercaseFieldsSerializerMixin, serializers.ModelSerializer):
    ship_id = serializers.PrimaryKeyRelatedField(
        source="ship",
        queryset=Ship.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Return
        fields = (
            "id",
            "spare_id",
            "command_id",
            "ship_id",
            "username",
            "returned_by",
            "remarks",
            "quantity_returned",
            "return_time",
        )
        read_only_fields = ("returned_by",)


def _resolve_initiate_dart_number(dart_number, pattern_number):
    """Mirror the legacy SurveyListView/DemandListView behaviour: if the row's own
    dart_number hasn't been set yet, look up the DART actually raised against this
    spare's pattern number instead of showing a blank/stale value."""
    stripped = (dart_number or "").strip()
    if stripped and stripped.lower() != "pending":
        return dart_number
    dart = (
        InitiateDart.objects.filter(spares__pattern=pattern_number)
        .order_by("-id")
        .first()
    )
    return dart.dart_number if dart else "pending"


class SurveySerializer(UppercaseFieldsSerializerMixin, serializers.ModelSerializer):
    initiate_dart_number = serializers.SerializerMethodField()

    class Meta:
        model = Survey
        fields = (
            "id",
            "issue_entry",
            "spare",
            "quantity_tosurvey",
            "dart_number",
            "initiate_dart_number",
            "is_iif",
            "is_iif_sync",
        )

    def get_initiate_dart_number(self, obj):
        return _resolve_initiate_dart_number(obj.dart_number, obj.spare.pattern_number)


class PostSurveySerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = PostSurvey
        fields = (
            "id",
            "spare",
            "issue_entry",
            "quantity_surveyed",
            "survey_type",
            "survey_number",
            "survey_report_date",
            "remarks",
            "has_pts",
            "created_by",
            "created_by_user",
            "dart_number",
        )
        read_only_fields = ("created_by_user",)


class DemandSerializer(UppercaseFieldsSerializerMixin, serializers.ModelSerializer):
    initiate_dart_number = serializers.SerializerMethodField()

    class Meta:
        model = Demand
        fields = (
            "id",
            "issue_entry",
            "spare",
            "quantity_todemand",
            "survey_entry",
            "dart_number",
            "initiate_dart_number",
            "is_iif",
            "is_iif_sync",
        )

    def get_initiate_dart_number(self, obj):
        return _resolve_initiate_dart_number(obj.dart_number, obj.spare.pattern_number)


class PostDemandSerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = PostDemand
        fields = (
            "id",
            "spare",
            "issue_entry",
            "quantity_demanded",
            "demand_number",
            "demand_date",
            "remarks",
            "created_by",
            "created_by_user",
            "dart_number",
        )
        read_only_fields = ("created_by_user",)


class ReceiveSerializer(UppercaseFieldsSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Receive
        fields = (
            "id",
            "spare",
            "issue_entry",
            "quantity_toreceive",
            "demand_entry",
            "dart_number",
        )


class PostReceiveSerializer(
    UppercaseFieldsSerializerMixin,
    serializers.ModelSerializer,
):
    class Meta:
        model = PostReceive
        fields = (
            "id",
            "spare",
            "issue_entry",
            "quantity_received",
            "receipt_number",
            "receive_date",
            "nac_status",
            "remarks",
            "dart_number",
            "created_by",
            "created_by_user",
        )
        read_only_fields = ("created_by_user",)


class PlannedRoutineSpareListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlannedRoutineSpareList
        fields = (
            "id",
            "pattern_number",
            "planned_routine_description",
            "quantity_required",
            "is_deleted",
        )


class SparesMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SparesMapping
        fields = ("id", "equipment_class", "equipment", "section_name")


class NotInCattedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotInCattedItem
        fields = ("id", "spare_id", "incatted_status", "is_deleted")


class MultiIssueItemSerializer(serializers.Serializer):
    spare = serializers.PrimaryKeyRelatedField(queryset=Spares.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class MultiIssueSerializer(serializers.Serializer):
    equipment = serializers.PrimaryKeyRelatedField(
        queryset=Issue._meta.get_field("equipment").remote_field.model.objects.all(),
        allow_null=True,
        required=False,
    )
    remarks = serializers.CharField(max_length=200)
    dart_number = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
    )
    items = MultiIssueItemSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        spare_ids = [item["spare"].pk for item in items]
        if len(spare_ids) != len(set(spare_ids)):
            raise serializers.ValidationError(
                "The same spare cannot be included more than once."
            )
        return items


class InitiateStockActionSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    equipment = serializers.PrimaryKeyRelatedField(
        queryset=Issue._meta.get_field("equipment").remote_field.model.objects.all(),
        allow_null=True,
        required=False,
    )
    dart_number = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
    )


class CompleteSurveySerializer(serializers.Serializer):
    quantity_surveyed = serializers.IntegerField(min_value=1)
    survey_type = serializers.ChoiceField(
        choices=PostSurvey.SURVEY_TYPE_CHOICES,
        default=PostSurvey.NORMAL,
    )
    survey_number = serializers.CharField(
        max_length=50,
        allow_blank=True,
        required=False,
    )
    survey_report_date = serializers.DateTimeField(required=False)
    remarks = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
    )
    has_pts = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs["survey_type"] == PostSurvey.NORMAL and not attrs.get("survey_number"):
            raise serializers.ValidationError(
                {"survey_number": "Survey number is required for a normal survey."}
            )
        return attrs


class CompleteDemandSerializer(serializers.Serializer):
    quantity_demanded = serializers.IntegerField(min_value=1)
    demand_number = serializers.CharField(max_length=50)
    demand_date = serializers.DateTimeField(required=False)
    remarks = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
    )


class CompleteReceiveSerializer(serializers.Serializer):
    quantity_received = serializers.IntegerField(min_value=1)
    receipt_number = serializers.CharField(max_length=50)
    receive_date = serializers.DateTimeField(required=False)
    nac_status = serializers.BooleanField(required=False, default=False)
    remarks = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
    )


class VerifyPatternSerializer(serializers.Serializer):
    pattern_number = serializers.CharField(max_length=500)
    category = serializers.CharField(max_length=30, required=False, allow_blank=True)


class UpdateSparePatternSerializer(serializers.Serializer):
    spare_pk = serializers.PrimaryKeyRelatedField(queryset=Spares.objects.all())
    pattern_number = serializers.CharField(max_length=500)
    category = serializers.ChoiceField(
        choices=(
            (Spares.PERMANENT, Spares.PERMANENT),
            (Spares.RETURNABLE, Spares.RETURNABLE),
            (Spares.CONSUMABLE, Spares.CONSUMABLE),
            ("P", "P"),
            ("R", "R"),
            ("C", "C"),
        ),
        required=False,
    )


class PatternIssueItemSerializer(serializers.Serializer):
    pattern_number = serializers.CharField(max_length=500)
    quantity_issued = serializers.IntegerField(min_value=1)


class PatternMultiIssueSerializer(serializers.Serializer):
    equipment = serializers.PrimaryKeyRelatedField(
        queryset=Issue._meta.get_field("equipment").remote_field.model.objects.all(),
        allow_null=True,
        required=False,
    )
    remarks = serializers.CharField(max_length=200)
    dart_number = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
    )
    items = PatternIssueItemSerializer(many=True, allow_empty=False)


class RequisitionDeleteSerializer(serializers.Serializer):
    pk = serializers.IntegerField(min_value=1)
    inventory_type = serializers.ChoiceField(choices=("OBS", "PIL", "WED", "MO"))
