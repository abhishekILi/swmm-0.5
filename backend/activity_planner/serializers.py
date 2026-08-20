from rest_framework import serializers

from master.models import Department, Ship

from .constants import (
    PlannerCategory,
    PlannerLane,
    PlannerPriority,
    PlannerStatus,
    get_lane_for_department,
)
from .models import Event, PlannerActivity


class EventSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "category",
            "description",
            "document",
            "created_by",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "created_by")


class PlannerActivityContractSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    subtitle = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    start_date = serializers.DateField(required=False, allow_null=True)
    start_time = serializers.TimeField(required=False, allow_null=True)
    end_time = serializers.TimeField(required=False, allow_null=True)
    end_date = serializers.TimeField(required=False, allow_null=True)
    time_label = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    lane = serializers.ChoiceField(choices=PlannerLane.choices)
    lane_label = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    department = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    category = serializers.ChoiceField(choices=PlannerCategory.choices)
    category_label = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    status = serializers.ChoiceField(choices=PlannerStatus.choices)
    status_label = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    priority = serializers.ChoiceField(
        choices=PlannerPriority.choices,
        required=False,
        allow_null=True,
    )
    priority_label = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )

    progress = serializers.IntegerField(min_value=0, max_value=100)
    active = serializers.BooleanField(required=False)
    delayed = serializers.BooleanField(required=False)
    conflict = serializers.BooleanField(required=False)
    selected = serializers.BooleanField(required=False)
    isolation = serializers.BooleanField(required=False)

    equipment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reference = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    location = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    ship = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    created_by = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    created_at = serializers.DateTimeField(required=False, allow_null=True)
    updated_at = serializers.DateTimeField(required=False, allow_null=True)


class PlannerSummaryCardSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField(min_value=0)


class PlannerNotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.ChoiceField(
        choices=[
            ("alert", "alert"),
            ("warn", "warn"),
            ("info", "info"),
        ]
    )
    icon = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    when = serializers.CharField()


class PlannerInboxMessageSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    unread = serializers.BooleanField()
    sender = serializers.CharField()
    subject = serializers.CharField()
    preview = serializers.CharField()
    when = serializers.CharField()


class PlannerActivitySerializer(serializers.ModelSerializer):
    department = serializers.CharField(source="department.name", read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        source="department",
        queryset=Department.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    ship = serializers.CharField(source="ship.name", read_only=True)
    ship_id = serializers.PrimaryKeyRelatedField(
        source="ship",
        queryset=Ship.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    lane_label = serializers.CharField(source="get_lane_display", read_only=True)
    category_label = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    priority_label = serializers.CharField(
        source="get_priority_display",
        read_only=True,
        allow_null=True,
    )
    time_label = serializers.SerializerMethodField()

    class Meta:
        model = PlannerActivity
        fields = (
            "id",
            "title",
            "subtitle",
            "description",
            "date",
            "start_time",
            "end_time",
            "time_label",
            "lane",
            "lane_label",
            "department",
            "department_id",
            "category",
            "category_label",
            "status",
            "status_label",
            "priority",
            "priority_label",
            "progress",
            "active",
            "delayed",
            "conflict",
            "selected",
            "isolation",
            "equipment",
            "reference",
            "location",
            "ship",
            "ship_id",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "department",
            "ship",
            "lane_label",
            "category_label",
            "status_label",
            "priority_label",
            "time_label",
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_time_label(self, obj):
        if not obj.end_time:
            return obj.start_time.strftime("%H%M hrs")
        return f"{obj.start_time.strftime('%H%M hrs')} - {obj.end_time.strftime('%H%M hrs')}"

    def validate_progress(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Progress must be between 0 and 100.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "End time must be after start time."}
            )
        if not attrs.get("lane") and attrs.get("department"):
            attrs["lane"] = get_lane_for_department(attrs["department"].name)
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            validated_data.setdefault("created_by", request.user)
        return super().create(validated_data)


class PlannerSummaryResponseSerializer(serializers.Serializer):
    category_cards = PlannerSummaryCardSerializer(many=True)
    conflict_count = serializers.IntegerField()
    delayed_count = serializers.IntegerField()
    active_count = serializers.IntegerField()
    upcoming_count = serializers.IntegerField()


class PlannerChoicesSerializer(serializers.Serializer):
    lanes = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    categories = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    statuses = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    priorities = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class PlannerConflictCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    a = serializers.CharField()
    when = serializers.CharField()


class PlannerOverdueCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    a = serializers.CharField()
    by = serializers.CharField()


class PlannerUpcomingCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    d = serializers.CharField()
    a = serializers.CharField()


class PlannerDashboardSerializer(serializers.Serializer):
    summary = PlannerSummaryResponseSerializer()
    notifications = PlannerNotificationSerializer(
        many=True, required=False, default=list
    )
    inbox = PlannerInboxMessageSerializer(many=True, required=False, default=list)
    conflicts = PlannerConflictCardSerializer(many=True)
    overdue = PlannerOverdueCardSerializer(many=True)
    upcoming = PlannerUpcomingCardSerializer(many=True)
    unread_count = serializers.IntegerField(required=False, default=0)
