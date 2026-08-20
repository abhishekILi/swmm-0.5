from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from master.models import Department

from .constants import PlannerCategory, PlannerPriority, PlannerStatus
from .models import Event, PlannerActivity
from .serializers import (
    EventSerializer,
    PlannerActivityContractSerializer,
    PlannerActivitySerializer,
    PlannerChoicesSerializer,
    PlannerDashboardSerializer,
    PlannerSummaryResponseSerializer,
)
from .services import (
    apply_activity_filters,
    build_conflict_cards,
    build_dart_trend,
    build_overdue_cards,
    build_overdue_darts,
    build_upcoming_cards,
    get_unified_activity_by_id,
    list_unified_activities,
    refresh_planner_state_for_queryset,
    summarize_unified_activities,
)


@extend_schema(tags=["Events"])
class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_permissions(self):
        if self.action in ("list", "ship_events"):
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        return Event.objects.ordered_desc()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user.CustomUser_profile)

    def ship_events(self, request):
        queryset = Event.objects.ordered_upcoming()

        ship_id = request.query_params.get("ship_id")
        if ship_id:
            queryset = queryset.for_ship(ship_id)

        queryset = queryset[:10]

        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)


@extend_schema(tags=["Operational Coordination Planner"])
class PlannerActivityViewSet(viewsets.ModelViewSet):
    serializer_class = PlannerActivitySerializer

    def get_queryset(self):
        queryset = PlannerActivity.objects.with_dashboard_relations()
        queryset = apply_activity_filters(queryset, self.request.query_params)
        refresh_planner_state_for_queryset(queryset)
        return queryset.ordered_schedule()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        activities = list_unified_activities(request.query_params)
        serializer = PlannerActivityContractSerializer(activities, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        match = get_unified_activity_by_id(kwargs.get("pk"))
        if not match:
            return Response({"detail": "Not found."}, status=404)
        serializer = PlannerActivityContractSerializer(match)
        return Response(serializer.data)

    def _get_manual_instance(self, activity_id):
        if not str(activity_id).startswith("activity_"):
            return None
        return PlannerActivity.objects.filter(
            id=str(activity_id).removeprefix("activity_")
        ).first()

    def update(self, request, *args, **kwargs):
        instance = self._get_manual_instance(kwargs.get("pk"))
        if not instance:
            return Response(
                {"detail": "Only manually-created activities can be edited."},
                status=404,
            )
        self.kwargs["pk"] = instance.pk
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self._get_manual_instance(kwargs.get("pk"))
        if not instance:
            return Response(
                {"detail": "Only manually-created activities can be deleted."},
                status=404,
            )
        affected_date = instance.date
        affected_lane = instance.lane
        instance.delete()

        from .services import refresh_planner_state_for_scope

        refresh_planner_state_for_scope(affected_date, affected_lane)
        return Response(status=204)

    @extend_schema(
        tags=["Operational Coordination Planner"],
        responses=PlannerSummaryResponseSerializer,
    )
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        activities = list_unified_activities(request.query_params)
        serializer = PlannerSummaryResponseSerializer(
            summarize_unified_activities(activities)
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Operational Coordination Planner"],
        responses=PlannerChoicesSerializer,
    )
    @action(detail=False, methods=["get"], url_path="choices")
    def choices(self, request):
        payload = {
            "lanes": [
                {"id": id, "label": name}
                for id, name in Department.objects.values_list("id", "name")
            ],
            "categories": [
                {"value": value, "label": label}
                for value, label in PlannerCategory.choices
            ],
            "statuses": [
                {"value": value, "label": label}
                for value, label in PlannerStatus.choices
            ],
            "priorities": [
                {"value": value, "label": label}
                for value, label in PlannerPriority.choices
            ],
        }
        serializer = PlannerChoicesSerializer(payload)
        return Response(serializer.data)

    @extend_schema(
        tags=["Operational Coordination Planner"],
        responses=PlannerDashboardSerializer,
    )
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        unified_activities = list_unified_activities(request.query_params)
        manual_queryset = self.get_queryset()
        payload = {
            "summary": summarize_unified_activities(unified_activities),
            "conflicts": build_conflict_cards(manual_queryset),
            "overdue": build_overdue_cards(manual_queryset),
            "upcoming": build_upcoming_cards(manual_queryset),
        }
        serializer = PlannerDashboardSerializer(payload)
        return Response(serializer.data)

    @extend_schema(tags=["Operational Coordination Planner"])
    @action(detail=False, methods=["get"], url_path="overdue-darts")
    def overdue_darts(self, request):
        department_id = request.query_params.get("department_id")
        rows = build_overdue_darts(department_id=department_id)
        return Response({"count": len(rows), "results": rows})

    @extend_schema(tags=["Operational Coordination Planner"])
    @action(detail=False, methods=["get"], url_path="dart-trend")
    def dart_trend(self, request):
        return Response(build_dart_trend())
