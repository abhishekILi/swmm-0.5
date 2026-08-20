import json
import os
import random

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from master.tasks import export_routine_excel_task
from swmm.async_jobs import accepted_task_response, dispatch_task, sync_task_response
from users.models import CustomUserProfile

from .models import (
    CoMessage,
    Department,
    HierarchyForChart,
    MemberDetail,
    OpsMaintenancePeriod,
    OrderDuty,
    Quote,
    RefitMaintenancePeriod,
    Ship,
    ShipRole,
    ShipRoleImage,
    UpdateEntry,
)
from .serializers import (
    CoMessageSerializer,
    GenericSuccessResponseSerializer,
    HierarchyForChartSerializer,
    MaintenanceNomenclatureDeleteSerializer,
    MaintenanceNomenclatureResponseSerializer,
    MaintenanceNomenclatureSerializer,
    MemberDetailSerializer,
    OrderDutySerializer,
    QuoteSerializer,
    RefitCompletionCreateSerializer,
    RefitCompletionResponseSerializer,
    RefitDelinquencyCreateSerializer,
    RefitDryDockingCreateSerializer,
    RefitOCRCreateSerializer,
    RefitSyncPayloadResponseSerializer,
    ShipKnowYourShipSerializer,
    ShipRoleSerializer,
    UpdateEntrySerializer,
)
from .utils import parse_iso_date, save_file_to_temp


@extend_schema(tags=["Master"])
class UpdateEntryViewSet(viewsets.ModelViewSet):
    queryset = UpdateEntry.objects.order_by("-uploaded_date")
    serializer_class = UpdateEntrySerializer


@extend_schema(tags=["Master"])
class ShipRoleViewSet(viewsets.ModelViewSet):
    queryset = ShipRole.objects.order_by("-uploaded_date")
    serializer_class = ShipRoleSerializer

    def _replace_images(self, ship, images):
        for image in ship.images.all():
            if image.image and os.path.isfile(image.image.path):
                os.remove(image.image.path)
        ship.images.all().delete()

        for image in images:
            ShipRoleImage.objects.create(ship=ship, image=image)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ship = serializer.save()

        for image in request.FILES.getlist("images"):
            ShipRoleImage.objects.create(ship=ship, image=image)

        return Response(self.get_serializer(ship).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        ship = self.get_object()
        serializer = self.get_serializer(ship, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        ship = serializer.save()

        images = request.FILES.getlist("images")
        if images:
            self._replace_images(ship, images)

        return Response(self.get_serializer(ship).data)


@extend_schema(tags=["Master"])
class MemberDetailViewSet(viewsets.ModelViewSet):
    queryset = MemberDetail.objects.order_by("-uploaded_date")
    serializer_class = MemberDetailSerializer

    def _save_image(self, instance, image):
        if image:
            instance.image_path = image
            instance.save(update_fields=["image_path"])

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        self._save_image(member, request.FILES.get("image"))
        return Response(
            self.get_serializer(member).data, status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        member = self.get_object()
        serializer = self.get_serializer(member, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        member = serializer.save()
        self._save_image(member, request.FILES.get("image"))
        return Response(self.get_serializer(member).data)


@extend_schema(tags=["Master"])
class OrderDutyViewSet(viewsets.ModelViewSet):
    queryset = OrderDuty.objects.order_by("-uploaded_at")
    serializer_class = OrderDutySerializer

    def get_permissions(self):
        if self.action in ("list", "daily_orders"):
            return [AllowAny()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="daily-orders",
    )
    def daily_orders(self, request):
        queryset = self.get_queryset().filter(source__iexact="daily order")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="duty-rosters")
    def duty_rosters(self, request):
        queryset = self.get_queryset().filter(source__iexact="duty roster")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="routines", permission_classes=[AllowAny])
    def get_routines(self, request):
        try:
            from ems.models import UniqueRoutineName
            routines = UniqueRoutineName.objects.all().values_list("name", flat=True).order_by("name")
            return Response({"routines": list(routines)})
        except Exception:
            return Response({"routines": []})

    @action(detail=False, methods=["post"], url_path="save-daily-order")
    def save_daily_order(self, request):
        data = request.data.copy()
        data["source"] = "daily order"
        data["from_date"] = parse_iso_date(data.get("date1") or data.get("date"))
        data["to_date"] = parse_iso_date(data.get("date2") or data.get("date"))
        data["date"] = parse_iso_date(data.get("date1") or data.get("date"))
        data["allocation_type"] = "SINGLE"

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="save-daily-orders")
    def save_daily_orders(self, request):
        import uuid
        try:
            allocations_json = request.data.get("allocations", "[]")
            allocations = json.loads(allocations_json)
        except (json.JSONDecodeError, ValueError):
            return Response(
                {"error": "allocations must be a valid JSON string"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(allocations, list) or not allocations:
            return Response(
                {"error": "allocations must be a non-empty array"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            batch_id = str(uuid.uuid4())
            with transaction.atomic():
                created_orders = []
                for allocation in allocations:
                    data = request.data.copy()
                    data["source"] = "daily order"
                    data["from_date"] = parse_iso_date(allocation.get("date"))
                    data["to_date"] = parse_iso_date(allocation.get("date"))
                    data["date"] = parse_iso_date(allocation.get("date"))
                    data["officer_details"] = allocation.get("officer_details")
                    data["routine_details"] = allocation.get("routine_details")
                    data["batch_id"] = batch_id
                    data["allocation_type"] = "MULTIPLE"

                    serializer = self.get_serializer(data=data)
                    serializer.is_valid(raise_exception=True)
                    order = serializer.save()
                    created_orders.append(order)

                return Response(
                    self.get_serializer(created_orders, many=True).data,
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["Master"])
class MaintenanceNomenclatureAPIView(APIView):
    def _serialize_ops(self, item):
        return {
            "id": item.id,
            "type": "OPERATIONAL",
            "name": item.name,
            "maintenance_period": item.maintenance_period,
            "occasion": item.occasion,
            "start_date": item.start_date,
            "end_date": item.end_date,
        }

    def _serialize_refit(self, item):
        return {
            "id": item.id,
            "type": "REFIT",
            "name": item.name,
            "maintenance_period": item.maintenance_period,
            "occasion": item.occasion,
            "start_date": item.actual_start_date or item.plan_start_date,
            "end_date": item.actual_end_date or item.plan_end_date,
        }

    @extend_schema(responses={200: MaintenanceNomenclatureResponseSerializer})
    def get(self, request):
        data = [
            self._serialize_ops(item)
            for item in OpsMaintenancePeriod.objects.order_by("id")
        ]
        data.extend(
            self._serialize_refit(item)
            for item in RefitMaintenancePeriod.objects.order_by("id")
        )
        return Response({"status": "success", "maint_nomenclature": data})

    @extend_schema(
        request=MaintenanceNomenclatureSerializer,
        responses={201: MaintenanceNomenclatureSerializer},
    )
    def post(self, request):
        serializer = MaintenanceNomenclatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["type"] == "OPERATIONAL":
            obj = OpsMaintenancePeriod.objects.create(
                name=data.get("name"),
                maintenance_period=data.get("maintenance_period"),
                occasion=data.get("occasion"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
            )
            return Response(self._serialize_ops(obj), status=status.HTTP_201_CREATED)

        obj = RefitMaintenancePeriod.objects.create(
            name=data.get("name"),
            maintenance_period=data.get("maintenance_period"),
            occasion=data.get("occasion"),
            actual_start_date=data.get("start_date"),
            actual_end_date=data.get("end_date"),
            plan_start_date=data.get("start_date"),
            plan_end_date=data.get("end_date"),
        )
        return Response(self._serialize_refit(obj), status=status.HTTP_201_CREATED)


@extend_schema(tags=["Master"])
class MaintenanceNomenclatureDeleteAPIView(APIView):
    @extend_schema(
        request=MaintenanceNomenclatureDeleteSerializer,
        responses={200: GenericSuccessResponseSerializer},
    )
    def post(self, request):
        serializer = MaintenanceNomenclatureDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        model = (
            OpsMaintenancePeriod
            if data["type"] == "OPERATIONAL"
            else RefitMaintenancePeriod
        )
        model.objects.filter(id=data["id"]).delete()
        return Response(
            {"success": True, "message": "Maintenance nomenclature deleted"}
        )

    @action(detail=False, methods=["post"], url_path="save-duty-roster")
    def save_duty_roster(self, request):
        data = request.data.copy()
        data["source"] = "duty roster"
        data["date"] = parse_iso_date(data.get("date"))
        data["from_date"] = data["date"]
        data["to_date"] = data["date"]

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Master"])
class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.order_by("-uploaded_date")
    serializer_class = QuoteSerializer

    def create(self, request, *args, **kwargs):
        quote_text = request.data.get("quoteText") or request.data.get("quote_text")
        if not quote_text:
            return Response(
                {"status": "error", "message": "Missing fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quote = Quote.objects.create(quote_text=quote_text)
        return Response(
            {
                "status": "success",
                "id": quote.id,
                "quoteText": quote.quote_text,
                "addedDate": quote.uploaded_date.strftime("%Y-%m-%d"),
                "is_active": quote.is_active,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        quote = self.get_object()
        quote_text = request.data.get("quoteText") or request.data.get("quote_text")
        if not quote_text:
            return Response(
                {"status": "error", "message": "Missing fields"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quote.quote_text = quote_text
        quote.save(update_fields=["quote_text"])
        return Response(
            {
                "status": "success",
                "id": quote.id,
                "quoteText": quote.quote_text,
                "addedDate": quote.uploaded_date.strftime("%Y-%m-%d"),
                "is_active": quote.is_active,
            }
        )

    @action(detail=False, methods=["get"], url_path="daily")
    def daily(self, request):
        today = timezone.now().date()

        active_quote = Quote.objects.filter(is_active=True).first()
        if active_quote:
            return Response({"status": "success", "quote": active_quote.quote_text})

        today_quote = Quote.objects.filter(last_displayed_date=today).first()
        if today_quote:
            return Response({"status": "success", "quote": today_quote.quote_text})

        unseen_quotes = list(Quote.objects.filter(is_displayed=False))
        if not unseen_quotes:
            return Response(
                {"status": "done", "message": "All quotes have been displayed"}
            )

        quote = random.SystemRandom().choice(unseen_quotes)
        quote.is_displayed = True
        quote.last_displayed_date = today
        quote.save(update_fields=["is_displayed", "last_displayed_date"])
        return Response({"status": "success", "quote": quote.quote_text})

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        Quote.objects.update(is_active=False)
        quote = self.get_object()
        quote.is_active = True
        quote.save(update_fields=["is_active"])
        return Response({"status": "success"})

    @action(detail=False, methods=["post"], url_path="deactivate-all")
    def deactivate_all(self, request):
        Quote.objects.update(is_active=False, is_displayed=False)
        return Response({"status": "success"})


@extend_schema_view(
    list=extend_schema(tags=["Master"]),
    retrieve=extend_schema(tags=["Master"]),
    create=extend_schema(tags=["Master"]),
    update=extend_schema(tags=["Master"]),
    partial_update=extend_schema(tags=["Master"]),
    destroy=extend_schema(tags=["Master"]),
    marquee=extend_schema(tags=["Master"]),
)
class CoMessageViewSet(viewsets.ModelViewSet):
    queryset = CoMessage.objects.order_by("-uploaded_date")
    serializer_class = CoMessageSerializer

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        return super().get_permissions()

    @action(
        detail=False, methods=["get"], permission_classes=[AllowAny], url_path="marquee"
    )
    def marquee(self, request):
        today = timezone.now().date()
        messages = CoMessage.objects.filter(valid_till_date__gte=today).order_by(
            "-uploaded_date"
        )
        data = [
            {
                "id": item.id,
                "message": item.message,
                "message_date": (
                    item.uploaded_date.strftime("%b %d, %Y")
                    if item.uploaded_date
                    else None
                ),
                "is_new": item.uploaded_date.date() == today,
            }
            for item in messages
        ]
        return Response(data)


@extend_schema_view(
    list=extend_schema(tags=["Master"]),
    retrieve=extend_schema(tags=["Master"]),
    create=extend_schema(tags=["Master"]),
    update=extend_schema(tags=["Master"]),
    partial_update=extend_schema(tags=["Master"]),
    destroy=extend_schema(tags=["Master"]),
    names=extend_schema(tags=["Master"]),
    available_users=extend_schema(tags=["Master"]),
    regulators_tree=extend_schema(tags=["Master"]),
    regulator_sailors=extend_schema(tags=["Master"]),
    tree=extend_schema(tags=["Master"]),
    nested=extend_schema(tags=["Master"]),
    toggle_sailor_regulator=extend_schema(tags=["Master"]),
    assign_regulator_bulk=extend_schema(tags=["Master"]),
)
class HierarchyForChartViewSet(viewsets.ModelViewSet):
    queryset = HierarchyForChart.objects.order_by("-date")
    serializer_class = HierarchyForChartSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return super().get_permissions()

    @action(
        detail=False, methods=["get"], permission_classes=[AllowAny], url_path="names"
    )
    def names(self, request):
        names = [
            {"id": node.id, "name": node.name}
            for node in HierarchyForChart.objects.order_by("date")
        ]
        return Response({"status": "success", "names": names})

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="available_users",
    )
    def available_users(self, request):
        """List personnel not assigned to another hierarchy node.

        ``exclude_node_id`` keeps a node's current user selectable while that
        node is being edited.
        """
        exclude_node_id = request.query_params.get("exclude_node_id")
        assigned_nodes = HierarchyForChart.objects.exclude(user__isnull=True)
        if exclude_node_id:
            assigned_nodes = assigned_nodes.exclude(pk=exclude_node_id)

        assigned_user_ids = assigned_nodes.values_list("user_id", flat=True)
        users = (
            CustomUserProfile.objects.filter(user_active=True, is_role=False)
            .exclude(pk__in=assigned_user_ids)
            .select_related("rank", "designation_master")
            .order_by("firstname", "lastname", "personal_number")
        )

        return Response(
            {
                "status": "success",
                "users": [
                    {
                        "id": user.id,
                        "name": " ".join(
                            part for part in (user.firstname, user.lastname) if part
                        ).strip()
                        or user.personal_number,
                        "rank": user.rank.name if user.rank_id else "",
                        "designation": user.designation
                        or (
                            user.designation_master.designation_name
                            if user.designation_master_id
                            else ""
                        ),
                        "personal_number": user.personal_number,
                        "photo": "",
                    }
                    for user in users
                ],
            }
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="regulators_tree",
    )
    def regulators_tree(self, request):
        departments_data = []

        # Get all departments
        departments = Department.objects.all()

        for dept in departments:
            regulators = []

            # Get regulators (nodes with is_regulator=True) in this department
            regulator_nodes = (
                HierarchyForChart.objects.filter(
                    is_regulator=True, user__department=dept
                )
                .select_related("user", "user__rank")
                .prefetch_related("assigned_sailors")
            )

            for node in regulator_nodes:
                assigned_count = node.assigned_sailors.count()
                regulator_data = {
                    "id": node.id,
                    "name": node.name,
                    "rank": node.user.rank.name
                    if node.user and node.user.rank
                    else None,
                    "designation": node.user.designation if node.user else None,
                    "assignedCount": assigned_count,
                }
                regulators.append(regulator_data)

            if regulators:
                dept_data = {
                    "id": dept.id,
                    "dep_name": dept.name,
                    "regulators": regulators,
                }
                departments_data.append(dept_data)

        return Response({"status": "success", "departments": departments_data})

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="regulator_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=True,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["get"],
        permission_classes=[AllowAny],
        url_path="regulator_sailors",
    )
    def regulator_sailors(self, request):
        regulator_id = request.query_params.get("regulator_id")
        if not regulator_id:
            return Response(
                {"status": "error", "message": "regulator_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            regulator = HierarchyForChart.objects.select_related(
                "user", "user__rank"
            ).get(id=int(regulator_id))
        except (HierarchyForChart.DoesNotExist, ValueError):
            return Response(
                {"status": "error", "message": "Regulator not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get assigned sailors
        assigned_sailors = regulator.assigned_sailors.all().select_related(
            "user", "user__rank"
        )
        assigned_data = [
            {
                "id": sailor.id,
                "name": sailor.name,
                "rank": sailor.user.rank.name
                if sailor.user and sailor.user.rank
                else None,
                "designation": sailor.user.designation if sailor.user else None,
                "personalNumber": sailor.user.personal_number if sailor.user else None,
            }
            for sailor in assigned_sailors
        ]

        # Get unassigned sailors (sailors not assigned to any regulator)
        unassigned_sailors = HierarchyForChart.objects.filter(
            node_type="sailor", assigned_regulator__isnull=True
        ).select_related("user", "user__rank")

        unassigned_data = [
            {
                "id": sailor.id,
                "name": sailor.name,
                "rank": sailor.user.rank.name
                if sailor.user and sailor.user.rank
                else None,
                "designation": sailor.user.designation if sailor.user else None,
                "personalNumber": sailor.user.personal_number if sailor.user else None,
            }
            for sailor in unassigned_sailors
        ]

        return Response(
            {
                "status": "success",
                "regulator": {
                    "id": regulator.id,
                    "name": regulator.name,
                },
                "assigned": assigned_data,
                "unassigned": unassigned_data,
            }
        )

    @action(
        detail=False, methods=["get"], permission_classes=[AllowAny], url_path="tree"
    )
    def tree(self, request):
        entries = HierarchyForChart.objects.order_by("date")
        data = [
            {
                "id": entry.id,
                "name": entry.name,
                "designation": entry.designation,
                "rank": entry.rank,
                "personal_number": entry.personal_number,
                "photo_url": entry.photo.url if entry.photo else "",
                "parent_id": entry.parent_id,
            }
            for entry in entries
        ]
        return Response({"status": "success", "ship_hierarchy": data})

    @action(
        detail=False, methods=["get"], permission_classes=[AllowAny], url_path="nested"
    )
    def nested(self, request):
        nodes = list(HierarchyForChart.objects.order_by("id"))
        node_map = {
            node.id: {
                "dbId": node.id,
                "type": node.node_type,
                "name": node.name,
                "rank": node.rank or "",
                "designation": node.designation or "",
                "personalNumber": node.personal_number or "",
                "photoUrl": node.photo.url if node.photo else None,
                "divisionName": node.division_name or "",
                "isRegulator": node.is_regulator,
                "selectedUserId": node.user_id,
                "children": [],
            }
            for node in nodes
        }

        root = None
        for node in nodes:
            if node.parent_id and node.parent_id in node_map:
                node_map[node.parent_id]["children"].append(node_map[node.id])
            elif node.is_commander_officer:
                root = node_map[node.id]

        return Response({"status": "success", "hierarchy": root})

    @action(detail=False, methods=["post"], url_path="toggle_sailor_regulator")
    def toggle_sailor_regulator(self, request):
        sailor_id = request.data.get("id")
        is_reg = request.data.get("is_reg")

        try:
            node = HierarchyForChart.objects.get(id=sailor_id, node_type="sailor")
        except HierarchyForChart.DoesNotExist:
            return Response(
                {"status": "error", "message": "Sailor not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        node.is_regulator = bool(is_reg)
        node.save(update_fields=["is_regulator"])
        return Response({"status": "success", "is_regulator": node.is_regulator})

    @action(detail=False, methods=["post"], url_path="assign_regulator_bulk")
    def assign_regulator_bulk(self, request):
        regulator_id = request.data.get("regulator_id")
        sailor_ids = request.data.get("sailor_ids") or []

        if not regulator_id:
            return Response(
                {"success": False, "error": "Regulator ID required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            regulator = HierarchyForChart.objects.select_related(
                "user__department"
            ).get(
                id=regulator_id,
                is_regulator=True,
            )
        except HierarchyForChart.DoesNotExist:
            return Response(
                {"success": False, "error": "Regulator not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        department = getattr(regulator.user, "department", None)
        HierarchyForChart.objects.filter(assigned_regulator=regulator).update(
            assigned_regulator=None
        )

        if sailor_ids:
            queryset = HierarchyForChart.objects.filter(id__in=sailor_ids)
            if department is not None:
                queryset = queryset.filter(user__department=department)
            queryset.update(assigned_regulator=regulator)

        return Response({"success": True, "assigned_count": len(sailor_ids)})


@extend_schema(tags=["Master"])
class ImportExcelFileView(APIView):
    def post(self, request):
        excel_file = request.FILES.get("excel_file")
        if not excel_file:
            return Response(
                {"detail": "Excel file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        save_path = save_file_to_temp(excel_file)
        return Response(
            {"detail": f"File saved to {save_path}"},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Master"], responses=ShipKnowYourShipSerializer)
class KnowYourShipAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, ship_external_id=None):
        if ship_external_id is not None:
            ship = Ship.objects.filter(ship_external_id=ship_external_id).first()
        else:
            ship = Ship.objects.first()

        if not ship:
            return Response(
                {"message": "Ship not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ShipKnowYourShipSerializer(
            ship,
            context={"request": request},
        )

        return Response(serializer.data)


@extend_schema(tags=["Master"])
class ExportRoutineExcelAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        department_id = getattr(
            getattr(request.user, "department", None),
            "id",
            None,
        )

        dispatch = dispatch_task(
            export_routine_excel_task,
            department_id,
        )

        if dispatch["queued"]:
            return accepted_task_response(
                request,
                dispatch["task"],
                "Routine Excel export queued for background processing.",
            )

        return sync_task_response(
            dispatch["result"],
            (
                "Background task service unavailable. "
                "Routine Excel export completed synchronously."
            ),
        )


# ─────────────────────────────────────────────────────────────
# CMMS Refit Integration Views
# ─────────────────────────────────────────────────────────────


@extend_schema(tags=["Master"])
class RefitPayloadView(APIView):
    """Return an empty refit sync payload."""

    def get(self, request):
        serializer = RefitSyncPayloadResponseSerializer(data={})
        serializer.is_valid()
        return Response(serializer.data)


@extend_schema(tags=["Master"])
class RefitCompletionsView(APIView):
    """Return an empty refit completions list or validate refit completion."""

    def get(self, request):
        return Response([])

    def post(self, request):
        """Validate a refit maintenance period payload and return a derived ID."""
        serializer = RefitCompletionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resp_data = {
            "id": 0,
            "Universal_ID_T_RefComp": f"U-RC-{timezone.now().date().isoformat()}-{serializer.validated_data.get('ship_code')}",
        }
        resp_serializer = RefitCompletionResponseSerializer(data=resp_data)
        resp_serializer.is_valid()
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Master"])
class RefitDelinquencyView(APIView):
    """Validate a delinquency detail payload and acknowledge receipt."""

    def post(self, request, uid):
        serializer = RefitDelinquencyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resp_serializer = GenericSuccessResponseSerializer(
            data={
                "success": True,
                "message": "Delinquency payload validated successfully.",
                "data": {
                    "refit_uid": uid,
                    "delinquency_code": serializer.validated_data.get(
                        "delinquency_code"
                    ),
                },
            }
        )
        resp_serializer.is_valid()
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Master"])
class RefitDryDockView(APIView):
    """Validate a drydocking payload and acknowledge receipt."""

    def post(self, request, uid):
        serializer = RefitDryDockingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resp_serializer = GenericSuccessResponseSerializer(
            data={
                "success": True,
                "message": "Drydocking payload validated successfully.",
                "data": {
                    "refit_uid": uid,
                    "dock_entry_date": serializer.validated_data.get("dock_entry_date"),
                },
            }
        )
        resp_serializer.is_valid()
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Master"])
class RefitOcrView(APIView):
    """Validate an OCR payload and acknowledge receipt."""

    def post(self, request, uid):
        serializer = RefitOCRCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        resp_serializer = GenericSuccessResponseSerializer(
            data={
                "success": True,
                "message": "OCR payload validated successfully.",
                "data": {
                    "refit_uid": uid,
                    "report_ref_no": serializer.validated_data.get("report_ref_no"),
                },
            }
        )
        resp_serializer.is_valid()
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)
