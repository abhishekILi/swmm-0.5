import json

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from dart.models import DartSpare
from ems.models import AddRoutineDetails, EquipmentName, RoutineDescription, SectionName
from ilms.models import DartMOSpare, Item, PlannedMOSpareList
from master.models import Department, MShipCommand, Ship
from wlms.models import DartWedSpare, PlannedWEDSpareList, SpareDataMap, WLMSSpare

from .excel import ExcelImportExportMixin
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
from .serializers import (
    AuthoritySerializer,
    CompleteDemandSerializer,
    CompleteReceiveSerializer,
    CompleteSurveySerializer,
    DemandSerializer,
    DenominationSerializer,
    EquipmentClassSerializer,
    InitiateStockActionSerializer,
    IssueListSerializer,
    IssueSerializer,
    MultiIssueSerializer,
    NotInCattedItemSerializer,
    PatternMultiIssueSerializer,
    PlannedRoutineSpareListSerializer,
    PostDemandSerializer,
    PostReceiveSerializer,
    PostSurveySerializer,
    ReceiveSerializer,
    RequisitionDeleteSerializer,
    ReturnSerializer,
    RoutineSpareUsageSerializer,
    SpareClassSerializer,
    SparesMappingSerializer,
    SparesSerializer,
    SurveySerializer,
    UpdateSparePatternSerializer,
    VerifyPatternSerializer,
)
from .utils import django_validation_error_detail, tagged_viewset


class CleanValidationMixin:
    def perform_create(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as error:
            raise DRFValidationError(django_validation_error_detail(error)) from error

    def perform_update(self, serializer):
        try:
            serializer.save()
        except DjangoValidationError as error:
            raise DRFValidationError(django_validation_error_detail(error)) from error


@extend_schema(tags=["OBS"])
class CleanValidationModelViewSet(
    ExcelImportExportMixin,
    CleanValidationMixin,
    viewsets.ModelViewSet,
):
    pass


def payload_pk(request, *keys):
    for key in keys:
        value = request.data.get(key)
        if value not in (None, ""):
            return value
    raise DRFValidationError({keys[0]: "This field is required."})


def request_user_department_id(request):
    profile = getattr(request.user, "user_profile", None)
    department_id = getattr(profile, "department_id", None)
    if department_id is None:
        department_id = getattr(request.user, "department_id", None)
    if department_id is None:
        raise DRFValidationError(
            {"department": "Authenticated user has no department assigned."}
        )
    return department_id


def user_display_name(user):
    profile = getattr(user, "user_profile", None)
    if profile:
        full_name = f"{profile.firstname or ''} {profile.lastname or ''}".strip()
        if full_name:
            return full_name

    get_full_name = getattr(user, "get_full_name", None)
    if callable(get_full_name):
        full_name = get_full_name()
        if full_name:
            return full_name

    return getattr(user, "username", "")


@tagged_viewset(
    "OBS",
    create_examples=[
        OpenApiExample(
            "Create spare class",
            value={"name": "ELECTRICAL", "department": None},
            request_only=True,
        )
    ],
)
class SpareClassViewSet(CleanValidationModelViewSet):
    queryset = SpareClass.objects.all()
    serializer_class = SpareClassSerializer

    @action(detail=False, methods=["get"], url_path="by-department")
    def by_department(self, request):
        department_id = request.query_params.get("department")
        queryset = self.get_queryset()
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return Response(self.get_serializer(queryset, many=True).data)


@tagged_viewset(
    "OBS",
    create_examples=[
        OpenApiExample(
            "Create equipment class",
            value={"name": "RADAR", "spare_class": 1},
            request_only=True,
        )
    ],
)
class EquipmentClassViewSet(CleanValidationModelViewSet):
    queryset = EquipmentClass.objects.select_related("spare_class").all()
    serializer_class = EquipmentClassSerializer

    @action(detail=False, methods=["get"], url_path="by-spare-class")
    def by_spare_class(self, request):
        spare_class_id = request.query_params.get("spare_class")
        queryset = self.get_queryset()
        if spare_class_id:
            queryset = queryset.filter(spare_class_id=spare_class_id)
        return Response(self.get_serializer(queryset, many=True).data)


@tagged_viewset(
    "OBS",
    create_examples=[
        OpenApiExample(
            "Create denomination",
            value={"name": "NOS", "department": None},
            request_only=True,
        )
    ],
)
class DenominationViewSet(CleanValidationModelViewSet):
    queryset = Denomination.objects.all()
    serializer_class = DenominationSerializer


@tagged_viewset(
    "OBS",
    create_examples=[
        OpenApiExample(
            "Create authority",
            value={"name": "NAVAL STORE AUTHORITY"},
            request_only=True,
        )
    ],
)
class AuthorityViewSet(CleanValidationModelViewSet):
    queryset = Authority.objects.all()
    serializer_class = AuthoritySerializer


@tagged_viewset("OBS")
class SparesViewSet(CleanValidationModelViewSet):
    queryset = Spares.objects.select_related(
        "authority",
        "denomination",
        "equipment_class",
        "equipment_class__spare_class",
    )
    serializer_class = SparesSerializer

    def get_excel_import_header_map(self):
        return {
            "SER": "",
            "SPARE CLASS": "spare_class_name",
            "EQUIPMENT CLASS": "equipment_class_name",
            "PATTERN NO": "pattern_number",
            "PATTERN NUMBER": "pattern_number",
            "DESCRIPTION": "description",
            "CATEGORY": "category",
            "DENOMINATION": "denomination_name",
            "QUANTITY AUTHORISED": "quantity_authorised",
            "QUANTITY AUTHORIZED": "quantity_authorised",
            "QUANTITY HELD": "quantity_available",
            "COMPARTMENT NAME": "compartment",
            "RACK POSITION": "rack_position",
            "RACK NUMBER": "rack_number",
            "BOX NO": "location",
            "BOX NUMBER": "location",
            "AUTHORITY": "authority_name",
            "D787J PAGE NUMBER": "page",
            "D787J LINE NUMBER": "line",
            "MO DEMAND NO": "mo_demand_number",
            "CRITICAL": "critical",
            "PICTURE PATH": "",
            "REMARKS": "remarks",
            "SHIP CUSTOMER CODE": "",
        }

    def _import_department(self):
        profile = getattr(self.request.user, "user_profile", None)
        department = getattr(profile, "department", None)
        if department is not None:
            return department
        department_id = getattr(profile, "department_id", None)
        if department_id:
            return Department.objects.filter(pk=department_id).first()
        return None

    @staticmethod
    def _clean_import_text(value, default=""):
        if value in (None, ""):
            return default
        if isinstance(value, float) and value.is_integer():
            return str(int(value)).strip()
        return str(value).strip()

    @staticmethod
    def _clean_import_int(value):
        if value in (None, ""):
            return 0
        try:
            return max(int(float(value)), 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _clean_import_bool(value):
        if isinstance(value, bool):
            return value
        return str(value or "").strip().upper() in {"1", "TRUE", "YES", "Y"}

    @staticmethod
    def _clean_import_category(value):
        category = str(value or "").strip().upper()
        return {
            "P": Spares.PERMANENT,
            "PERMANENT": Spares.PERMANENT,
            "R": Spares.RETURNABLE,
            "RETURNABLE": Spares.RETURNABLE,
            "C": Spares.CONSUMABLE,
            "CONSUMABLE": Spares.CONSUMABLE,
        }.get(category, Spares.PERMANENT)

    @staticmethod
    def _get_or_create_authority(name):
        clean_name = SparesViewSet._clean_import_text(name, "UNKNOWN").upper()
        authority = Authority.objects.filter(name__iexact=clean_name).first()
        if authority is not None:
            return authority
        return Authority.objects.create(name=clean_name)

    @staticmethod
    def _get_or_create_spare_class(name, department):
        clean_name = SparesViewSet._clean_import_text(name, "UNKNOWN").upper()
        spare_class = SpareClass.objects.filter(
            name__iexact=clean_name,
            department=department,
        ).first()
        if spare_class is not None:
            return spare_class
        return SpareClass.objects.create(name=clean_name, department=department)

    @staticmethod
    def _get_or_create_equipment_class(name, spare_class):
        clean_name = SparesViewSet._clean_import_text(name, "UNKNOWN").upper()
        equipment_class = EquipmentClass.objects.filter(
            name__iexact=clean_name,
            spare_class=spare_class,
        ).first()
        if equipment_class is not None:
            return equipment_class
        return EquipmentClass.objects.create(name=clean_name, spare_class=spare_class)

    @staticmethod
    def _get_or_create_denomination(name, department):
        clean_name = SparesViewSet._clean_import_text(name, "NOS").upper()
        denomination = Denomination.objects.filter(
            name__iexact=clean_name,
            department=department,
        ).first()
        if denomination is not None:
            return denomination
        return Denomination.objects.create(name=clean_name, department=department)

    def build_excel_import_payload(self, row, serializer_fields):
        if "equipment_class_name" not in row and "authority_name" not in row:
            return super().build_excel_import_payload(row, serializer_fields)

        department = self._import_department()
        spare_class = self._get_or_create_spare_class(
            row.get("spare_class_name"),
            department,
        )
        equipment_class = self._get_or_create_equipment_class(
            row.get("equipment_class_name"),
            spare_class,
        )
        denomination = self._get_or_create_denomination(
            row.get("denomination_name"),
            department,
        )
        authority = self._get_or_create_authority(row.get("authority_name"))
        quantity_authorised = self._clean_import_int(row.get("quantity_authorised"))
        quantity_available = self._clean_import_int(row.get("quantity_available"))
        quantity_authorised = max(quantity_authorised, quantity_available)

        return {
            "equipment_class": equipment_class.pk,
            "pattern_number": self._clean_import_text(row.get("pattern_number")),
            "description": self._clean_import_text(row.get("description")),
            "category": self._clean_import_category(row.get("category")),
            "critical": self._clean_import_bool(row.get("critical")),
            "compartment": self._clean_import_text(row.get("compartment"), "UNKNOWN"),
            "location": self._clean_import_text(row.get("location"), "UNKNOWN"),
            "rack_position": self._clean_import_text(
                row.get("rack_position"),
                "UNKNOWN",
            ),
            "rack_number": self._clean_import_text(row.get("rack_number"), "UNKNOWN"),
            "denomination": denomination.pk,
            "quantity_authorised": quantity_authorised,
            "quantity_available": quantity_available,
            "authority": authority.pk,
            "page": self._clean_import_text(row.get("page")),
            "line": self._clean_import_text(row.get("line")),
            "remarks": self._clean_import_text(row.get("remarks")),
            "mo_demand_number": self._clean_import_text(row.get("mo_demand_number")),
            "is_obs": True,
        }

    def _filtered_queryset(self, include_query=True):
        queryset = self.get_queryset()
        filters = {
            "equipment_class__spare_class__department_id": (
                self.request.query_params.get("department")
            ),
            "equipment_class__spare_class_id": (
                self.request.query_params.get("spare_class")
            ),
            "equipment_class_id": self.request.query_params.get("equipment_class"),
            "category": self.request.query_params.get("category"),
            "authority_id": self.request.query_params.get("authority"),
        }
        for field_name, value in filters.items():
            if value not in (None, ""):
                queryset = queryset.filter(**{field_name: value})

        text_filters = {
            "pattern_number__icontains": self.request.query_params.get(
                "pattern_number"
            ),
            "description__icontains": self.request.query_params.get("description"),
            "equipment_class__name__icontains": (
                self.request.query_params.get("equipment")
            ),
            "remarks__icontains": self.request.query_params.get("remarks"),
        }
        for field_name, value in text_filters.items():
            if value:
                queryset = queryset.filter(**{field_name: value})

        query = self.request.query_params.get("q")
        if include_query and query:
            queryset = queryset.filter(
                Q(pattern_number__icontains=query)
                | Q(description__icontains=query)
                | Q(equipment_class__name__icontains=query)
            )

        critical = self.request.query_params.get("critical")
        if critical is not None:
            queryset = queryset.filter(
                critical=critical.lower() in {"1", "true", "yes"}
            )
        return queryset.distinct()

    @action(detail=False, methods=["get"])
    def search(self, request):
        queryset = self._filtered_queryset()
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="low-stock")
    def low_stock(self, request):
        queryset = self._filtered_queryset().filter(
            quantity_authorised__gt=0,
            quantity_available__lte=F("quantity_authorised") / 2,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def critical(self, request):
        queryset = self._filtered_queryset().filter(critical=True)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="d787j-deficiency")
    def d787j_deficiency(self, request):
        queryset = self._filtered_queryset().filter(authority__name__iexact="D787J")
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["post"], url_path="verify-pattern")
    def verify_pattern(self, request):
        category_map = {
            "P": Spares.PERMANENT,
            "C": Spares.CONSUMABLE,
            "R": Spares.RETURNABLE,
        }
        serializer = VerifyPatternSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pattern_number = serializer.validated_data["pattern_number"].strip().upper()
        expected_category = (
            serializer.validated_data.get("category", "").strip().upper()
        )
        expected_category = category_map.get(expected_category, expected_category)

        def build_response(source, code, description, raw_category, denomination):
            mapped_category = category_map.get(
                (raw_category or "").strip().upper(),
                (raw_category or Spares.PERMANENT).strip().upper(),
            )
            is_match = not expected_category or mapped_category == expected_category
            return Response(
                {
                    "valid": is_match,
                    "source": source,
                    "pattern_number": code,
                    "item_code": code,
                    "description": description,
                    "item_desc": description,
                    "category": mapped_category,
                    "crp_category": mapped_category,
                    "expected_category": expected_category,
                    "category_mismatch": not is_match,
                    "denomination": denomination,
                }
            )

        item = Item.objects.filter(item_code__iexact=pattern_number).first()
        if item is not None:
            return build_response(
                "ITEM",
                item.item_code,
                item.item_desc,
                item.crp_category,
                item.item_deno,
            )

        wlms_item = WLMSSpare.objects.filter(item_code__iexact=pattern_number).first()
        if wlms_item is not None:
            return build_response(
                "WLMS",
                wlms_item.item_code,
                wlms_item.item_desc,
                wlms_item.category,
                wlms_item.denom_id,
            )

        return Response(
            {
                "valid": False,
                "pattern_number": pattern_number,
                "error": "Pattern number not found",
            }
        )

    @action(detail=False, methods=["post"], url_path="update-pattern")
    def update_pattern(self, request):
        serializer = UpdateSparePatternSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        spare = serializer.validated_data["spare_pk"]
        category = serializer.validated_data.get("category", spare.category)
        category_map = {
            "P": Spares.PERMANENT,
            "C": Spares.CONSUMABLE,
            "R": Spares.RETURNABLE,
        }
        category = category_map.get(category, category)
        spare.pattern_number = (
            serializer.validated_data["pattern_number"].strip().upper()
        )
        spare.save(update_fields=["pattern_number"])
        NotInCattedItem.objects.filter(
            spare_id=spare,
            is_deleted=False,
        ).update(incatted_status=True, is_deleted=True)
        redirect_map = {
            Spares.PERMANENT: "/obs/survey_list/",
            Spares.RETURNABLE: "/obs/iif_list/",
            Spares.CONSUMABLE: "/obs/demand_list/",
        }
        return Response(
            {
                "success": True,
                "spare": spare.pk,
                "pattern_number": spare.pattern_number,
                "redirect_url": redirect_map.get(category, "/obs/iif_list/"),
            }
        )

    @action(detail=False, methods=["get"], url_path="defect-requisition")
    def defect_requisition(self, request):
        dart_id = request.query_params.get("dart")
        dart_spares = DartSpare.objects.filter(is_delete=False).select_related(
            "dart",
            "equipment_id",
        )
        if dart_id:
            dart_spares = dart_spares.filter(dart_id=dart_id)
        patterns = [entry.pattern.upper() for entry in dart_spares]
        onboard_by_pattern = {
            spare.pattern_number.upper(): spare
            for spare in self.get_queryset().filter(pattern_number__in=patterns)
        }
        data = []
        for entry in dart_spares:
            onboard_spare = onboard_by_pattern.get(entry.pattern.upper())
            data.append(
                {
                    "dart_spare_id": entry.pk,
                    "dart": entry.dart_id,
                    "dart_number": entry.dart.dart_number,
                    "pattern_number": entry.pattern,
                    "description": entry.description,
                    "quantity_required": entry.quantity,
                    "onboard_spare": (onboard_spare.pk if onboard_spare else None),
                    "quantity_available": (
                        onboard_spare.quantity_available if onboard_spare else 0
                    ),
                    "available_onboard": bool(
                        onboard_spare
                        and onboard_spare.quantity_available >= entry.quantity
                    ),
                }
            )
        return Response(data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        queryset = self._filtered_queryset()
        totals = queryset.aggregate(
            authorised_quantity=Sum("quantity_authorised"),
            available_quantity=Sum("quantity_available"),
        )
        spare_ids = queryset.values_list("pk", flat=True)
        issued_quantity = (
            Issue.objects.filter(spare_id__in=spare_ids).aggregate(
                total=Sum("quantity_issued")
            )["total"]
            or 0
        )
        return Response(
            {
                "total_spares": queryset.count(),
                "critical_spares": queryset.filter(critical=True).count(),
                "stock_out_spares": queryset.filter(quantity_available=0).count(),
                "low_stock_spares": queryset.filter(
                    quantity_authorised__gt=0,
                    quantity_available__lte=F("quantity_authorised") / 2,
                ).count(),
                "authorised_quantity": totals["authorised_quantity"] or 0,
                "available_quantity": totals["available_quantity"] or 0,
                "issued_quantity": issued_quantity,
                "pending_surveys": Survey.objects.filter(
                    spare_id__in=spare_ids
                ).count(),
                "pending_demands": Demand.objects.filter(
                    spare_id__in=spare_ids
                ).count(),
                "pending_receipts": Receive.objects.filter(
                    spare_id__in=spare_ids
                ).count(),
                "not_in_catted_items": NotInCattedItem.objects.filter(
                    spare_id__in=spare_ids,
                    incatted_status=False,
                    is_deleted=False,
                ).count(),
            }
        )

    @action(detail=False, methods=["get"], url_path="ship-dashboard")
    def ship_dashboard(self, request):
        queryset = self._filtered_queryset(include_query=False)
        spares = list(queryset)
        spare_ids = [spare.pk for spare in spares]

        def stock_bucket(spare):
            if spare.quantity_available <= 0:
                return "unavailable"
            if (
                spare.quantity_authorised > 0
                and spare.quantity_available * 2 <= spare.quantity_authorised
            ):
                return "at_risk"
            return "available"

        def availability_group(key, label, group_spares):
            buckets = {
                "available": 0,
                "at_risk": 0,
                "unavailable": 0,
            }
            for spare in group_spares:
                buckets[stock_bucket(spare)] += 1

            total = len(group_spares)
            percentage = round((buckets["available"] / total) * 100) if total else 0
            if percentage >= 90:
                availability_status = "EXCELLENT"
            elif percentage >= 75:
                availability_status = "GOOD"
            else:
                availability_status = "AT RISK"

            return {
                "key": key,
                "label": label,
                **buckets,
                "percentage": percentage,
                "status": availability_status,
                "segments": [
                    {
                        "label": "Available",
                        "value": buckets["available"],
                        "color": "#1FD162",
                    },
                    {
                        "label": "At Risk",
                        "value": buckets["at_risk"],
                        "color": "#FF9B35",
                    },
                    {
                        "label": "Unavailable",
                        "value": buckets["unavailable"],
                        "color": "#FF4747",
                    },
                ],
            }

        all_group = availability_group("obs", "OBS", spares)
        availability_groups = [
            all_group,
            availability_group(
                "critical",
                "Critical Spares",
                [spare for spare in spares if spare.critical],
            ),
            availability_group(
                "consumables",
                "Consumables",
                [spare for spare in spares if spare.category == Spares.CONSUMABLE],
            ),
            availability_group(
                "repairables",
                "Repairables",
                [spare for spare in spares if spare.category == Spares.RETURNABLE],
            ),
            availability_group(
                "tools",
                "Tools & Test Equip.",
                [
                    spare
                    for spare in spares
                    if "TOOL" in spare.description.upper()
                    or "TEST" in spare.description.upper()
                ],
            ),
        ]

        critical_shortages = sum(
            1
            for spare in spares
            if spare.critical and stock_bucket(spare) != "available"
        )
        stock_out_items = all_group["unavailable"]
        below_minimum = all_group["at_risk"]
        pending_demands = Demand.objects.filter(spare_id__in=spare_ids).count()
        pending_replenishments = Receive.objects.filter(spare_id__in=spare_ids).count()

        equipment_class_ids = {spare.equipment_class_id for spare in spares}
        mapped_equipment = (
            SparesMapping.objects.filter(equipment_class_id__in=equipment_class_ids)
            .select_related(
                "equipment",
                "equipment__department",
                "equipment__equipment",
                "equipment__equipment_type_f_key",
            )
            .distinct()
        )
        equipment_by_class = {}
        for mapping in mapped_equipment:
            equipment_by_class.setdefault(mapping.equipment_class_id, []).append(
                mapping.equipment
            )

        supportability = {}
        impacted_equipment_ids = set()
        for spare in spares:
            mapped_items = equipment_by_class.get(spare.equipment_class_id, [])
            for equipment in mapped_items:
                if equipment is None:
                    continue
                equipment_name = (
                    getattr(equipment, "nomenclature", None)
                    or getattr(equipment.equipment_type_f_key, "equipment_desc", None)
                    or str(equipment.equipment or "Unclassified System")
                )
                system = supportability.setdefault(
                    equipment_name,
                    {"total": 0, "available": 0},
                )
                system["total"] += 1
                if stock_bucket(spare) == "available":
                    system["available"] += 1
                else:
                    impacted_equipment_ids.add(equipment.pk)

        supportability_items = []
        for title, values in supportability.items():
            percentage = round((values["available"] / values["total"]) * 100)
            supportability_items.append(
                {
                    "title": title,
                    "availability": percentage,
                    "status": "Good" if percentage >= 75 else "At Risk",
                }
            )
        supportability_items.sort(key=lambda item: item["availability"])

        low_stock_spares = sorted(
            [spare for spare in spares if stock_bucket(spare) != "available"],
            key=lambda spare: (
                stock_bucket(spare) != "unavailable",
                not spare.critical,
                spare.quantity_available,
            ),
        )
        stock_health = []
        for spare in low_stock_spares[:5]:
            is_stock_out = stock_bucket(spare) == "unavailable"
            stock_health.append(
                {
                    "id": spare.pk,
                    "name": spare.description or spare.pattern_number,
                    "value": (
                        "Stock-Out"
                        if is_stock_out
                        else f"{spare.quantity_available} Available"
                    ),
                    "status": "critical" if is_stock_out else "warning",
                }
            )

        decision_support = []
        for spare in low_stock_spares[:5]:
            decision_support.append(
                {
                    "name": (f"Replenish {spare.description or spare.pattern_number}"),
                    "priority": (
                        "HIGH"
                        if spare.critical or stock_bucket(spare) == "unavailable"
                        else "MEDIUM"
                    ),
                }
            )

        departments = {}
        for spare in spares:
            department = spare.equipment_class.spare_class.department
            department_name = department.name if department else "Unassigned"
            department_values = departments.setdefault(
                department_name,
                {"total": 0, "available": 0},
            )
            department_values["total"] += 1
            if stock_bucket(spare) == "available":
                department_values["available"] += 1

        department_items = []
        for name, values in departments.items():
            percentage = round((values["available"] / values["total"]) * 100)
            department_items.append(
                {
                    "name": name,
                    "percent": percentage,
                    "status": (
                        "Excellent"
                        if percentage >= 95
                        else ("Good" if percentage >= 75 else "At Risk")
                    ),
                }
            )
        department_items.sort(key=lambda item: item["name"])

        issue_totals = {
            Spares.RETURNABLE: 0,
            Spares.CONSUMABLE: 0,
            "critical": 0,
        }
        issues = Issue.objects.filter(spare_id__in=spare_ids).select_related("spare")
        for issue in issues:
            if issue.spare.category in issue_totals:
                issue_totals[issue.spare.category] += issue.quantity_issued
            if issue.spare.critical:
                issue_totals["critical"] += issue.quantity_issued

        trend = [
            {
                "label": "Repairables",
                "value": issue_totals[Spares.RETURNABLE],
                "color": "#22C55E",
            },
            {
                "label": "Critical Spares",
                "value": issue_totals["critical"],
                "color": "#FF5B5B",
            },
            {
                "label": "Consumables",
                "value": issue_totals[Spares.CONSUMABLE],
                "color": "#0A84FF",
            },
        ]

        current_month = timezone.now().date().replace(day=1)
        month_keys = [
            current_month - relativedelta(months=offset) for offset in range(5, 0, -1)
        ]
        monthly_issue_totals = {
            month: {
                "repairables": 0,
                "critical_spares": 0,
                "consumables": 0,
            }
            for month in month_keys
        }
        for issue in issues:
            issue_month = issue.date_of_issue.replace(day=1)
            if issue_month not in monthly_issue_totals:
                continue
            if issue.spare.critical:
                monthly_issue_totals[issue_month]["critical_spares"] += (
                    issue.quantity_issued
                )
            elif issue.spare.category == Spares.RETURNABLE:
                monthly_issue_totals[issue_month]["repairables"] += (
                    issue.quantity_issued
                )
            elif issue.spare.category == Spares.CONSUMABLE:
                monthly_issue_totals[issue_month]["consumables"] += (
                    issue.quantity_issued
                )

        trend_months = [
            {
                "label": month.strftime("%b %Y"),
                "repairables": values["repairables"],
                "critical_spares": values["critical_spares"],
                "consumables": values["consumables"],
            }
            for month, values in monthly_issue_totals.items()
        ]

        search_result = None
        query = request.query_params.get("q", "").strip()
        selected_spare = next(
            (spare for spare in low_stock_spares if spare.critical),
            queryset.first(),
        )
        if query:
            selected_spare = queryset.filter(
                Q(pattern_number__icontains=query)
                | Q(description__icontains=query)
                | Q(equipment_class__name__icontains=query)
            ).first()
        if selected_spare:
            on_order = (
                Receive.objects.filter(spare=selected_spare).aggregate(
                    total=Sum("quantity_toreceive")
                )["total"]
                or 0
            )
            committed = (
                IssueList.objects.filter(issue_entry__spare=selected_spare).aggregate(
                    total=Sum("quantity_toreturn")
                )["total"]
                or 0
            )
            image_url = None
            if selected_spare.image:
                image_name = selected_spare.image.name or ""
                frontend_public_prefixes = (
                    "../frontend/public/",
                    "frontend/public/",
                    "/frontend/public/",
                )
                frontend_path = next(
                    (
                        image_name.removeprefix(prefix).lstrip("/")
                        for prefix in frontend_public_prefixes
                        if image_name.startswith(prefix)
                    ),
                    None,
                )
                if frontend_path:
                    image_url = "/" + frontend_path.replace("assets/", "assests/", 1)
                else:
                    try:
                        image_url = request.build_absolute_uri(selected_spare.image.url)
                    except ValueError:
                        image_url = None
            search_result = {
                "id": selected_spare.pk,
                "pattern_number": selected_spare.pattern_number,
                "description": selected_spare.description,
                "critical": selected_spare.critical,
                "stock_status": stock_bucket(selected_spare).upper(),
                "denomination": (
                    selected_spare.denomination.name
                    if selected_spare.denomination
                    else ""
                ),
                "category": selected_spare.category,
                "image": image_url,
                "on_hand": selected_spare.quantity_available,
                "committed": committed,
                "available": max(
                    selected_spare.quantity_available - committed,
                    0,
                ),
                "on_order": on_order,
                "minimum_stock": selected_spare.quantity_authorised // 2,
                "location": selected_spare.location,
            }

        availability_percentage = all_group["percentage"]
        return Response(
            {
                "kpis": [
                    {
                        "key": "critical_shortages",
                        "title": "Critical Shortages",
                        "count": critical_shortages,
                        "icon_color": "#EF4444",
                    },
                    {
                        "key": "stock_out",
                        "title": "Stock-Out Items",
                        "count": stock_out_items,
                        "icon_color": "#F59E0B",
                    },
                    {
                        "key": "below_minimum",
                        "title": "Below Min Stock",
                        "count": below_minimum,
                        "icon_color": "#EAB308",
                    },
                    {
                        "key": "pending_demands",
                        "title": "Pending Demands",
                        "count": pending_demands,
                        "icon_color": "#3B82F6",
                    },
                    {
                        "key": "pending_replenishment",
                        "title": "Pending Replenishment",
                        "count": pending_replenishments,
                        "icon_color": "#8B5CF6",
                    },
                ],
                "availability": {
                    "total_items": len(spares),
                    "available_items": all_group["available"],
                    "at_risk_items": all_group["at_risk"],
                    "unavailable_items": all_group["unavailable"],
                    "overall_percentage": availability_percentage,
                    "status": all_group["status"],
                    "groups": availability_groups,
                },
                "supportability": supportability_items[:5],
                "maintenance_impact": {
                    "metrics": [
                        {
                            "topValue": len(impacted_equipment_ids),
                            "topLabel": "Equipment Affected",
                        },
                        {
                            "topValue": Issue.objects.filter(
                                spare_id__in=[spare.pk for spare in low_stock_spares]
                            ).count(),
                            "topLabel": "Maintenance",
                        },
                        {
                            "topValue": sum(
                                1
                                for item in supportability_items
                                if "WEAPON" in item["title"].upper()
                                and item["status"] == "At Risk"
                            ),
                            "topLabel": "Weapon System Affected",
                        },
                        {
                            "topValue": sum(
                                1
                                for item in supportability_items
                                if item["status"] == "At Risk"
                            ),
                            "topLabel": "Critical Systems At Risk",
                        },
                    ],
                    "systems": [
                        {
                            "title": item["title"],
                            "status": (
                                "HIGH" if item["availability"] < 50 else "MEDIUM"
                            ),
                        }
                        for item in supportability_items[:3]
                    ],
                },
                "stock_health": stock_health,
                "decision_support": decision_support,
                "logistics": {
                    "demand_queued": pending_demands,
                    "under_procurement": PostDemand.objects.filter(
                        spare_id__in=spare_ids
                    ).count(),
                    "under_repair": PostSurvey.objects.filter(
                        spare_id__in=spare_ids,
                        spare__category=Spares.RETURNABLE,
                    ).count(),
                    "expected_to_arrive": pending_replenishments,
                    "delayed_overdue": 0,
                    "available_onboard": all_group["available"],
                    "expected_availability": [
                        {
                            "label": "Demand",
                            "value": pending_demands,
                            "color": "#2ECC71",
                        },
                        {
                            "label": "Procurement",
                            "value": PostDemand.objects.filter(
                                spare_id__in=spare_ids
                            ).count(),
                            "color": "#F5A623",
                        },
                        {
                            "label": "Expected",
                            "value": pending_replenishments,
                            "color": "#0A84FF",
                        },
                        {
                            "label": "Overdue",
                            "value": 0,
                            "color": "#FF5B5B",
                        },
                    ],
                },
                "trend": trend,
                "trend_months": trend_months,
                "departments": department_items,
                "search_result": search_result,
            }
        )

    @action(detail=True, methods=["get"], url_path="detail-summary")
    def detail_summary(self, request, pk=None):
        spare = self.get_object()
        image_url = None
        if (
            spare.image
            and spare.image.name
            and not spare.image.name.endswith("default.png")
        ):
            image_url = request.build_absolute_uri(spare.image.url)
        return Response(
            {
                "success": True,
                "data": {
                    "id": spare.pk,
                    "pattern_number": spare.pattern_number or "-",
                    "description": spare.description or "-",
                    "category": spare.category or "-",
                    "equipment_class": (
                        spare.equipment_class.name if spare.equipment_class else "-"
                    ),
                    "spare_class": (
                        spare.equipment_class.spare_class.name
                        if spare.equipment_class and spare.equipment_class.spare_class
                        else "-"
                    ),
                    "department": (
                        spare.equipment_class.spare_class.department.name
                        if (
                            spare.equipment_class
                            and spare.equipment_class.spare_class
                            and spare.equipment_class.spare_class.department
                        )
                        else "-"
                    ),
                    "authority": spare.authority.name if spare.authority else "-",
                    "compartment": spare.compartment or "-",
                    "location": spare.location or "-",
                    "rack_position": spare.rack_position or "-",
                    "rack_number": spare.rack_number or "-",
                    "denomination": (
                        spare.denomination.name if spare.denomination else "-"
                    ),
                    "quantity_authorised": spare.quantity_authorised or 0,
                    "quantity_available": spare.quantity_available or 0,
                    "images": [image_url] if image_url else ["/media/default.png"],
                    "is_critical": spare.critical,
                },
            }
        )

    @action(detail=False, methods=["post"], url_path="check-wed-mapping")
    def check_wed_mapping(self, request):
        raw_pks = request.data.get("pks", [])
        if isinstance(raw_pks, str):
            raw_pks = [pk.strip() for pk in raw_pks.split(",") if pk.strip()]
        if not raw_pks:
            raise DRFValidationError({"pks": "At least one WED spare id is required."})

        unmapped_items = []
        planned_wed_spares = PlannedWEDSpareList.objects.select_related(
            "planned_spares_description__wlms_spare_id__eqpt",
        ).filter(pk__in=raw_pks)
        for wed_spare_entry in planned_wed_spares:
            plan_desc = wed_spare_entry.planned_spares_description
            wlms_spare = plan_desc.wlms_spare_id if plan_desc else None
            if not wlms_spare or not wlms_spare.eqpt:
                unmapped_items.append(
                    {
                        "pattern_number": (
                            wlms_spare.item_code if wlms_spare else wed_spare_entry.pk
                        ),
                        "description": wlms_spare.item_desc if wlms_spare else "",
                    }
                )
                continue
            if not SpareDataMap.objects.filter(wed_equipment=wlms_spare.eqpt).exists():
                unmapped_items.append(
                    {
                        "pattern_number": wlms_spare.item_code,
                        "description": wlms_spare.item_desc,
                        "eqpt_name": wlms_spare.eqpt.eqpt_name,
                    }
                )

        seen = set()
        unique_unmapped = []
        for item in unmapped_items:
            key = item["pattern_number"]
            if key not in seen:
                seen.add(key)
                unique_unmapped.append(item)
        return Response(
            {
                "all_mapped": len(unique_unmapped) == 0,
                "unmapped": unique_unmapped,
            }
        )

    def _normalize_pattern_issue_payload(self, request):
        data = request.data.copy()
        raw_items = data.get("items", data.get("table_data", []))
        if isinstance(raw_items, str):
            try:
                raw_items = json.loads(raw_items)
            except json.JSONDecodeError as error:
                raise DRFValidationError(
                    {"items": "Invalid table data format."}
                ) from error
        items = []
        for item in raw_items:
            pattern_number = item.get("pattern_number") or item.get("pattern")
            quantity = (
                item.get("quantity_issued")
                or item.get("quantity")
                or item.get("qty")
                or 0
            )
            items.append(
                {
                    "pattern_number": pattern_number,
                    "quantity_issued": quantity,
                }
            )
        data["items"] = items
        if "equipment" not in data and data.get("equipment_name"):
            data["equipment"] = data["equipment_name"]
        return data

    def _create_pattern_issues(self, request, update_dart_spares=False):
        serializer = PatternMultiIssueSerializer(
            data=self._normalize_pattern_issue_payload(request)
        )
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data["remarks"].upper().strip()
        dart_number = serializer.validated_data.get("dart_number", "").upper()
        equipment = serializer.validated_data.get("equipment")
        items = serializer.validated_data["items"]
        success_spares = []
        error_spares = []
        issues = []

        with transaction.atomic():
            for item in items:
                pattern_number = item["pattern_number"].strip().upper()
                quantity_issued = item["quantity_issued"]
                spare = (
                    Spares.objects.select_for_update()
                    .filter(pattern_number__iexact=pattern_number)
                    .first()
                )
                if spare is None:
                    error_spares.append(
                        {
                            "pattern_number": pattern_number,
                            "error": "Spare not found",
                        }
                    )
                    continue
                if quantity_issued > spare.quantity_available:
                    error_spares.append(
                        {
                            "pattern_number": pattern_number,
                            "error": "Issued quantity exceeds available",
                        }
                    )
                    continue

                try:
                    issue = Issue.objects.create(
                        spare=spare,
                        equipment=equipment,
                        username=request.user.CustomUser_profile,
                        quantity_issued=quantity_issued,
                        remarks=remarks,
                        dart_number=dart_number,
                    )
                except DjangoValidationError as error:
                    error_spares.append(
                        {
                            "pattern_number": pattern_number,
                            "error": django_validation_error_detail(error),
                        }
                    )
                    continue

                IssueList.objects.create(
                    issue_entry=issue,
                    quantity_toreturn=quantity_issued,
                    dart_number=dart_number,
                )
                if remarks not in {"TY LOAN", "OTHER"}:
                    if spare.category == Spares.CONSUMABLE:
                        Demand.objects.create(
                            issue_entry=issue,
                            spare=spare,
                            quantity_todemand=quantity_issued,
                            dart_number=dart_number,
                        )
                    else:
                        Survey.objects.create(
                            issue_entry=issue,
                            spare=spare,
                            quantity_tosurvey=quantity_issued,
                            dart_number=dart_number,
                        )

                if update_dart_spares and dart_number:
                    dart_spare = (
                        DartSpare.objects.select_for_update()
                        .filter(
                            dart__dart_number__iexact=dart_number,
                            pattern__iexact=pattern_number,
                            is_delete=False,
                        )
                        .first()
                    )
                    if dart_spare:
                        if quantity_issued >= dart_spare.quantity:
                            dart_spare.delete()
                        else:
                            dart_spare.quantity -= quantity_issued
                            dart_spare.save(update_fields=["quantity"])

                success_spares.append(pattern_number)
                issues.append(issue)

        return Response(
            {
                "status": "success",
                "issued": success_spares,
                "errors": error_spares,
                "dart_number": dart_number,
                "issues": IssueSerializer(issues, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="routine-multi-issue")
    def routine_multi_issue(self, request):
        return self._create_pattern_issues(request)

    @action(detail=False, methods=["post"], url_path="defect-multi-issue")
    def defect_multi_issue(self, request):
        return self._create_pattern_issues(request, update_dart_spares=True)

    @extend_schema(
        request=MultiIssueSerializer,
        responses={201: IssueSerializer(many=True)},
        tags=["OBS"],
    )
    @action(detail=False, methods=["post"], url_path="multi-issue")
    def multi_issue(self, request):
        serializer = MultiIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = serializer.validated_data["items"]
        spare_ids = [item["spare"].pk for item in items]

        with transaction.atomic():
            locked_spares = {
                spare.pk: spare
                for spare in Spares.objects.select_for_update().filter(pk__in=spare_ids)
            }
            errors = []
            for item in items:
                spare = locked_spares[item["spare"].pk]
                if item["quantity"] > spare.quantity_available:
                    errors.append(
                        {
                            "spare": spare.pk,
                            "pattern_number": spare.pattern_number,
                            "error": (
                                "Issue quantity cannot exceed available quantity."
                            ),
                        }
                    )
            if errors:
                raise DRFValidationError({"items": errors})

            issues = []
            remarks = serializer.validated_data["remarks"].upper()
            dart_number = serializer.validated_data.get(
                "dart_number",
                "",
            ).upper()
            equipment = serializer.validated_data.get("equipment")
            for item in items:
                spare = locked_spares[item["spare"].pk]
                issue = Issue.objects.create(
                    spare=spare,
                    equipment=equipment,
                    username=request.user.CustomUser_profile,
                    quantity_issued=item["quantity"],
                    remarks=remarks,
                    dart_number=dart_number,
                )
                IssueList.objects.create(
                    issue_entry=issue,
                    quantity_toreturn=item["quantity"],
                    dart_number=dart_number,
                )
                if remarks not in {"TY LOAN", "OTHER"}:
                    if spare.category == Spares.CONSUMABLE:
                        Demand.objects.create(
                            issue_entry=issue,
                            spare=spare,
                            quantity_todemand=item["quantity"],
                            dart_number=dart_number,
                        )
                    else:
                        Survey.objects.create(
                            issue_entry=issue,
                            spare=spare,
                            quantity_tosurvey=item["quantity"],
                            dart_number=dart_number,
                        )
                issues.append(issue)

        return Response(
            {"issues": IssueSerializer(issues, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        spare = self.get_object()
        return Response(
            {
                "issues": IssueSerializer(
                    spare.issues.select_related("equipment", "username"),
                    many=True,
                ).data,
                "returns": ReturnSerializer(
                    spare.returns.select_related("command_id", "ship"),
                    many=True,
                ).data,
                "surveys": SurveySerializer(
                    spare.surveys.select_related("issue_entry"),
                    many=True,
                ).data,
                "post_surveys": PostSurveySerializer(
                    spare.post_surveys.select_related("issue_entry"),
                    many=True,
                ).data,
                "demands": DemandSerializer(
                    spare.demands.select_related(
                        "issue_entry",
                        "survey_entry",
                    ),
                    many=True,
                ).data,
                "post_demands": PostDemandSerializer(
                    spare.post_demands.select_related("issue_entry"),
                    many=True,
                ).data,
                "receives": ReceiveSerializer(
                    spare.receives.select_related(
                        "issue_entry",
                        "demand_entry",
                    ),
                    many=True,
                ).data,
                "post_receives": PostReceiveSerializer(
                    spare.post_receives.select_related("issue_entry"),
                    many=True,
                ).data,
            }
        )

    @extend_schema(
        request=InitiateStockActionSerializer,
        responses={201: SurveySerializer},
        tags=["OBS"],
    )
    @action(detail=True, methods=["post"], url_path="initiate-survey")
    def initiate_survey(self, request, pk=None):
        spare = self.get_object()
        serializer = InitiateStockActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            issue = Issue.objects.create(
                spare=spare,
                equipment=serializer.validated_data.get("equipment"),
                username=request.user.CustomUser_profile,
                quantity_issued=quantity,
                remarks="INITIATED FROM REQUISITION",
                dart_number=serializer.validated_data.get(
                    "dart_number",
                    "",
                ),
            )
            survey = Survey.objects.create(
                spare=spare,
                issue_entry=issue,
                quantity_tosurvey=quantity,
                dart_number=issue.dart_number,
            )

        return Response(
            {
                "issue": IssueSerializer(issue).data,
                "survey": SurveySerializer(survey).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def initiate_survey_from_payload(self, request):
        self.kwargs[self.lookup_url_kwarg or self.lookup_field] = payload_pk(
            request,
            "spare_id",
            "spare",
            "pk",
            "id",
        )
        return self.initiate_survey(request, pk=self.kwargs["pk"])

    @extend_schema(
        request=InitiateStockActionSerializer,
        responses={201: DemandSerializer},
        tags=["OBS"],
    )
    @action(detail=True, methods=["post"], url_path="initiate-demand")
    def initiate_demand(self, request, pk=None):
        spare = self.get_object()
        serializer = InitiateStockActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            issue = Issue.objects.create(
                spare=spare,
                equipment=serializer.validated_data.get("equipment"),
                username=request.user.CustomUser_profile,
                quantity_issued=quantity,
                remarks="INITIATED FROM REQUISITION",
                dart_number=serializer.validated_data.get(
                    "dart_number",
                    "",
                ),
            )
            demand = Demand.objects.create(
                spare=spare,
                issue_entry=issue,
                quantity_todemand=quantity,
                dart_number=issue.dart_number,
            )

        return Response(
            {
                "issue": IssueSerializer(issue).data,
                "demand": DemandSerializer(demand).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def initiate_demand_from_payload(self, request):
        self.kwargs[self.lookup_url_kwarg or self.lookup_field] = payload_pk(
            request,
            "spare_id",
            "spare",
            "pk",
            "id",
        )
        return self.initiate_demand(request, pk=self.kwargs["pk"])

    @action(detail=False, methods=["get"], url_path="master-dropdown")
    def master_dropdown(self, request):
        department_id = request_user_department_id(request)
        equipment_classes = (
            EquipmentClass.objects.filter(spare_class__department_id=department_id)
            .order_by("name")
            .distinct("name")
        )
        departments = Department.objects.exclude(name__in=["ADMIN"]).order_by("name")
        sections = SectionName.objects.filter(department_id=department_id).order_by(
            "name"
        )
        equipment_list = EquipmentName.objects.all().order_by("name")

        return Response(
            {
                "equipment_classes": EquipmentClassSerializer(
                    equipment_classes, many=True
                ).data,
                "departments": [
                    {"id": department.id, "name": department.name}
                    for department in departments
                ],
                "sections": [
                    {"id": section.id, "name": section.name} for section in sections
                ],
                "equipment_list": [
                    {"id": equipment.id, "name": equipment.name}
                    for equipment in equipment_list
                ],
            }
        )

    @action(detail=False, methods=["get"], url_path="defect-spares-for-dart")
    def defect_spares_for_dart(self, request, pk=None):
        dart_id = pk or request.query_params.get("dart")
        if not dart_id:
            raise DRFValidationError({"dart": "DART id is required."})

        ids_param = request.query_params.get("ids", "")
        ids = [value for value in ids_param.split(",") if value]
        queryset = (
            self.get_queryset().filter(pk__in=ids)
            if ids
            else self.get_queryset().none()
        )

        dart_spare = (
            DartSpare.objects.filter(dart_id=dart_id).select_related("dart").first()
        )

        return Response(
            {
                "dart": dart_id,
                "dart_number": dart_spare.dart.dart_number if dart_spare else None,
                "spares": self.get_serializer(queryset, many=True).data,
            }
        )

    @staticmethod
    def _survey_history_row(entry):
        return {
            "pattern_number": entry.spare.pattern_number,
            "equipment_class": entry.spare.equipment_class.name,
            "description": entry.spare.description,
            "quantity": entry.quantity_surveyed,
            "survey_number": entry.survey_number,
            "date": (
                timezone.localtime(entry.survey_report_date).strftime("%Y-%m-%dT%H:%M")
                if entry.survey_report_date
                else None
            ),
            "remarks": entry.remarks,
            "created_by": entry.created_by,
        }

    def _spare_history(self, spare_ids, department_id):
        history_issue = [
            {
                "pattern_number": entry.spare.pattern_number,
                "equipment_class": entry.spare.equipment_class.name,
                "description": entry.spare.description,
                "username": user_display_name(entry.username),
                "quantity": str(entry.quantity_issued),
                "date": (
                    timezone.localtime(entry.issue_time).strftime("%Y-%m-%dT%H:%M")
                    if entry.issue_time
                    else None
                ),
                "remarks": entry.remarks,
                "nomenclature": entry.equipment.nomenclature if entry.equipment else "",
                "authority": entry.spare.authority.name,
            }
            for entry in Issue.objects.select_related(
                "spare",
                "spare__equipment_class",
                "spare__authority",
                "equipment",
                "username",
                "username__user_profile",
            ).filter(
                spare_id__in=spare_ids,
                spare__equipment_class__spare_class__department_id=department_id,
            )
        ]

        history_return = [
            {
                "pattern_number": entry.spare_id.pattern_number,
                "equipment_class": entry.spare_id.equipment_class.name,
                "description": entry.spare_id.description,
                "username": entry.username,
                "remarks": entry.remarks,
            }
            for entry in Return.objects.filter(
                spare_id__in=spare_ids,
                spare_id__equipment_class__spare_class__department_id=department_id,
            ).select_related("spare_id", "spare_id__equipment_class")
        ]

        history_survey_bypassed = [
            self._survey_history_row(entry)
            for entry in PostSurvey.objects.filter(
                spare_id__in=spare_ids,
                spare__equipment_class__spare_class__department_id=department_id,
                survey_number__iexact="ONE-TIME APPROVAL",
            ).select_related("spare", "spare__equipment_class")
        ]

        history_survey = [
            self._survey_history_row(entry)
            for entry in PostSurvey.objects.filter(
                spare_id__in=spare_ids,
                spare__equipment_class__spare_class__department_id=department_id,
            )
            .exclude(survey_number__iexact="NA")
            .exclude(survey_number__iexact="-NA-")
            .exclude(survey_number__iexact="PTS")
            .select_related("spare", "spare__equipment_class")
        ]

        history_demand = [
            {
                "pattern_number": entry.spare.pattern_number,
                "equipment_class": entry.spare.equipment_class.name,
                "description": entry.spare.description,
                "quantity": entry.quantity_demanded,
                "demand_number": entry.demand_number,
                "date": (
                    timezone.localtime(entry.demand_date).strftime("%Y-%m-%dT%H:%M")
                    if entry.demand_date
                    else None
                ),
                "remarks": entry.remarks,
                "created_by": entry.created_by,
            }
            for entry in PostDemand.objects.filter(
                spare_id__in=spare_ids,
                spare__equipment_class__spare_class__department_id=department_id,
            ).select_related("spare", "spare__equipment_class")
        ]

        history_receive = [
            {
                "pattern_number": entry.spare.pattern_number,
                "equipment_class": entry.spare.equipment_class.name,
                "description": entry.spare.description,
                "quantity": entry.quantity_received,
                "receipt_number": entry.receipt_number,
                "date": (
                    timezone.localtime(entry.receive_date).strftime("%Y-%m-%dT%H:%M")
                    if entry.receive_date
                    else None
                ),
                "nac_status": entry.nac_status,
                "remarks": entry.remarks,
                "created_by": entry.created_by,
            }
            for entry in PostReceive.objects.filter(
                spare_id__in=spare_ids,
                spare__equipment_class__spare_class__department_id=department_id,
            ).select_related("spare", "spare__equipment_class")
        ]

        return {
            "history_issue": history_issue,
            "history_return": history_return,
            "history_survey_bypassed": history_survey_bypassed,
            "history_survey": history_survey,
            "history_demand": history_demand,
            "history_receive": history_receive,
        }

    @action(detail=False, methods=["get"], url_path="search-history")
    def search_history(self, request):
        department_id = request_user_department_id(request)
        ids_param = request.query_params.get("spare_ids", "")
        spare_ids = [value for value in ids_param.split(",") if value]

        if not spare_ids:
            spare_ids = list(
                self.get_queryset()
                .filter(equipment_class__spare_class__department_id=department_id)
                .values_list("id", flat=True)
            )

        return Response(self._spare_history(spare_ids, department_id))

    @action(detail=False, methods=["post"], url_path="add-from-ilms")
    def add_from_ilms(self, request):
        pattern_number = (request.data.get("pattern_number") or "").strip().upper()
        if not pattern_number:
            raise DRFValidationError({"pattern_number": "This field is required."})

        try:
            quantity_required = int(request.data.get("quantity_required") or 0)
        except (TypeError, ValueError):
            raise DRFValidationError(
                {"quantity_required": "A valid quantity is required."}
            )
        if quantity_required <= 0:
            raise DRFValidationError(
                {"quantity_required": "Quantity must be greater than zero."}
            )

        spare = Spares.objects.filter(pattern_number=pattern_number).first()
        if not spare:
            raise DRFValidationError({"pattern_number": "Spare not found."})

        equipment = None
        equipment_id = request.data.get("equipment_name")
        if equipment_id:
            equipment = EquipmentName.objects.filter(pk=equipment_id).first()

        remarks = request.data.get("remarks", "")

        with transaction.atomic():
            issue = Issue.objects.create(
                spare=spare,
                username=request.user.CustomUser_profile,
                equipment=equipment,
                remarks=remarks,
                quantity_issued=quantity_required,
                dart_number="",
            )

            spare.quantity_authorised = quantity_required
            spare.quantity_available = 0
            spare.save(update_fields=["quantity_available", "quantity_authorised"])

            issue_list, created = IssueList.objects.get_or_create(
                issue_entry=issue,
                defaults={"quantity_toreturn": quantity_required},
            )
            if not created:
                issue_list.quantity_toreturn = (
                    F("quantity_toreturn") + quantity_required
                )
                issue_list.save(update_fields=["quantity_toreturn"])
                issue_list.refresh_from_db()

        return Response(
            {
                "issue": IssueSerializer(issue).data,
                "issue_list_id": issue_list.pk,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="submit-validated-inventory-data",
    )
    def submit_validated_inventory_data(self, request):
        department_id = request_user_department_id(request)
        rows = request.data.get("rows")
        if rows is None:
            rows = request.data.get("ShipInventory", {}).get("data", [])
        if not isinstance(rows, list):
            raise DRFValidationError({"rows": "A list of rows is required."})

        saved = 0
        skipped_duplicates = 0
        failed = 0
        errors = []

        with transaction.atomic():
            for index, row in enumerate(rows):
                row_data = row.get("data", row) if isinstance(row, dict) else {}
                pattern_number = (row_data.get("pattern_number") or "").strip().upper()
                if not pattern_number:
                    failed += 1
                    errors.append(
                        {"row_index": index, "error": "pattern_number is required."}
                    )
                    continue

                if Spares.objects.filter(pattern_number=pattern_number).exists():
                    skipped_duplicates += 1
                    continue

                try:
                    spare_class, _ = SpareClass.objects.get_or_create(
                        name=(row_data.get("spare_class") or "UNCATEGORISED")
                        .strip()
                        .upper(),
                        department_id=department_id,
                    )
                    equipment_class, _ = EquipmentClass.objects.get_or_create(
                        name=(row_data.get("equipment_class") or "UNCATEGORISED")
                        .strip()
                        .upper(),
                        spare_class=spare_class,
                    )
                    authority, _ = Authority.objects.get_or_create(
                        name=(row_data.get("authority") or "UNKNOWN").strip().upper(),
                    )
                    denomination = None
                    if row_data.get("denomination"):
                        denomination, _ = Denomination.objects.get_or_create(
                            name=row_data["denomination"].strip().upper(),
                            department_id=department_id,
                        )

                    Spares.objects.create(
                        pattern_number=pattern_number,
                        description=row_data.get("description", ""),
                        equipment_class=equipment_class,
                        authority=authority,
                        denomination=denomination,
                        category=row_data.get("category", Spares.PERMANENT),
                        quantity_authorised=row_data.get("quantity_authorised", 0),
                        quantity_available=row_data.get("quantity_available", 0),
                        compartment=row_data.get("compartment", "UNKNOWN"),
                        location=row_data.get("location", "UNKNOWN"),
                        remarks=row_data.get("remarks", ""),
                    )
                    saved += 1
                except Exception as error:
                    # Row-level failures must not abort the rest of the batch.
                    failed += 1
                    errors.append({"row_index": index, "error": str(error)})

        return Response(
            {
                "success": saved > 0,
                "message": f"{saved} rows saved successfully.",
                "details": {
                    "total_rows": len(rows),
                    "saved": saved,
                    "skipped_duplicates": skipped_duplicates,
                    "failed": failed,
                    "errors": errors,
                },
            }
        )


@tagged_viewset("OBS")
class RoutineSpareUsageViewSet(CleanValidationModelViewSet):
    queryset = RoutineSpareUsage.objects.select_related(
        "routine",
        "routine_description",
        "spare",
    ).all()
    serializer_class = RoutineSpareUsageSerializer

    @action(detail=False, methods=["get"])
    def routines(self, request):
        equipment_id = request.query_params.get("equipment")
        if not equipment_id:
            raise DRFValidationError({"equipment": "Equipment id is required."})
        routines = AddRoutineDetails.objects.filter(
            equipment_name_id=equipment_id
        ).select_related("routine_name")
        return Response(
            [
                {
                    "id": routine.pk,
                    "name": routine.routine_name.name,
                    "routine_number": routine.routine_no,
                    "dart_number": routine.dart_number,
                }
                for routine in routines
            ]
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="routine-descriptions",
    )
    def routine_descriptions(self, request):
        routine_id = request.query_params.get("routine")
        if not routine_id:
            raise DRFValidationError({"routine": "Routine id is required."})
        descriptions = RoutineDescription.objects.filter(
            add_routine_details_id=routine_id
        )
        return Response(
            [
                {
                    "id": description.pk,
                    "description": description.routine_description,
                    "routine_number": description.routine_no,
                    "dart_number": description.dart_number,
                }
                for description in descriptions
            ]
        )


@tagged_viewset("OBS")
class IssueViewSet(CleanValidationModelViewSet):
    queryset = Issue.objects.select_related("spare", "username").all()
    serializer_class = IssueSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        spare_id = self.request.query_params.get("spare")
        remarks = self.request.query_params.get("remarks")
        department_id = self.request.query_params.get("department")
        if spare_id:
            queryset = queryset.filter(spare_id=spare_id)
        if remarks:
            queryset = queryset.filter(remarks__iexact=remarks)
        if department_id:
            queryset = queryset.filter(
                spare__equipment_class__spare_class__department_id=(department_id)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="issued-to-maintainers")
    def issued_to_maintainers(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @action(detail=False, methods=["get"], url_path="ty-loan")
    def ty_loan(self, request):
        issues = self.get_queryset().filter(remarks__iexact="TY LOAN")
        spare_ids = issues.values_list("spare_id", flat=True)
        returns = Return.objects.filter(spare_id_id__in=spare_ids).order_by("id")
        return_map = {}
        for returned_spare in returns:
            key = (returned_spare.spare_id_id, returned_spare.quantity_returned)
            return_map.setdefault(key, []).append(returned_spare)

        data = []
        for issue in issues:
            key = (issue.spare_id, issue.quantity_issued)
            matched_return = None
            if return_map.get(key):
                matched_return = return_map[key].pop(0)
            data.append(
                {
                    "issue": IssueSerializer(issue).data,
                    "return": (
                        ReturnSerializer(matched_return).data
                        if matched_return
                        else None
                    ),
                }
            )
        return Response(data)


@tagged_viewset("OBS")
class IssueListViewSet(CleanValidationModelViewSet):
    queryset = IssueList.objects.select_related("issue_entry").all()
    serializer_class = IssueListSerializer


@tagged_viewset("OBS")
class ReturnViewSet(CleanValidationModelViewSet):
    queryset = Return.objects.select_related(
        "spare_id",
        "command_id",
        "ship",
        "returned_by",
    ).all()
    serializer_class = ReturnSerializer

    def perform_create(self, serializer):
        serializer.save(
            returned_by=self.request.user.CustomUser_profile,
            username=self.request.user.get_username(),
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        spare_id = self.request.query_params.get("spare")
        command_id = self.request.query_params.get("command")
        ship_id = self.request.query_params.get("ship")
        if spare_id:
            queryset = queryset.filter(spare_id_id=spare_id)
        if command_id:
            queryset = queryset.filter(command_id_id=command_id)
        if ship_id:
            queryset = queryset.filter(ship_id=ship_id)
        return queryset

    @action(detail=False, methods=["get"], url_path="returned-spares")
    def returned_spares(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @action(detail=False, methods=["get"])
    def commands(self, request):
        commands = MShipCommand.objects.exclude(command_name__isnull=True).exclude(
            command_name__iexact="NA"
        )
        return Response(
            [
                {
                    "id": command.pk,
                    "command_code": command.command_code,
                    "command_name": command.command_name,
                }
                for command in commands
            ]
        )

    @action(detail=False, methods=["get"])
    def ships(self, request):
        queryset = Ship.objects.all()
        command_id = request.query_params.get("command")
        if command_id:
            queryset = queryset.filter(command_id=command_id)
        return Response(
            [
                {
                    "id": ship.pk,
                    "code": ship.code,
                    "name": ship.name,
                    "command": ship.command_id,
                }
                for ship in queryset
            ]
        )


@tagged_viewset("OBS")
class SurveyViewSet(CleanValidationModelViewSet):
    queryset = Survey.objects.select_related("issue_entry", "spare").all()
    serializer_class = SurveySerializer

    @extend_schema(
        request=CompleteSurveySerializer,
        responses={201: PostSurveySerializer},
        tags=["OBS"],
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        serializer = CompleteSurveySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity_surveyed"]

        with transaction.atomic():
            survey = Survey.objects.select_for_update().get(pk=self.get_object().pk)
            if quantity > survey.quantity_tosurvey:
                raise DRFValidationError(
                    {
                        "quantity_surveyed": (
                            "Surveyed quantity cannot exceed pending quantity."
                        )
                    }
                )
            survey_type = serializer.validated_data["survey_type"]
            survey_number = serializer.validated_data.get("survey_number", "")
            if survey_type != PostSurvey.NORMAL:
                survey_number = survey_type.replace("_", "-")

            post_survey = PostSurvey.objects.create(
                spare=survey.spare,
                issue_entry=survey.issue_entry,
                quantity_surveyed=quantity,
                survey_type=survey_type,
                survey_number=survey_number,
                survey_report_date=serializer.validated_data.get(
                    "survey_report_date",
                    timezone.now(),
                ),
                remarks=serializer.validated_data.get("remarks", ""),
                has_pts=(
                    serializer.validated_data["has_pts"]
                    or survey_type == PostSurvey.PTS
                ),
                created_by=request.user.get_username(),
                created_by_user=request.user.CustomUser_profile,
                dart_number=survey.dart_number,
            )
            demand = Demand.objects.create(
                spare=survey.spare,
                issue_entry=survey.issue_entry,
                quantity_todemand=quantity,
                survey_entry=post_survey,
                dart_number=survey.dart_number,
                is_iif=survey.is_iif,
            )
            remaining_quantity = survey.quantity_tosurvey - quantity
            if remaining_quantity:
                survey.quantity_tosurvey = remaining_quantity
                survey.save(update_fields=["quantity_tosurvey"])
            else:
                survey.delete()

        return Response(
            {
                "post_survey": PostSurveySerializer(post_survey).data,
                "demand": DemandSerializer(demand).data,
            },
            status=status.HTTP_201_CREATED,
        )


@tagged_viewset("OBS")
class PostSurveyViewSet(CleanValidationModelViewSet):
    queryset = PostSurvey.objects.select_related(
        "issue_entry",
        "spare",
        "created_by_user",
    ).all()
    serializer_class = PostSurveySerializer

    @action(detail=False, methods=["get"], url_path="pts-list")
    def pts_list(self, request):
        queryset = self.get_queryset().filter(
            survey_number__in=["PTS", "OPDEM", "ONETIME APPROVAL"],
            has_pts=True,
            spare__equipment_class__spare_class__department_id=(
                request_user_department_id(request)
            ),
        )
        return Response(self.get_serializer(queryset, many=True).data)


@tagged_viewset("OBS")
class DemandViewSet(CleanValidationModelViewSet):
    queryset = Demand.objects.select_related(
        "issue_entry",
        "spare",
        "survey_entry",
    )
    serializer_class = DemandSerializer

    @extend_schema(
        request=CompleteDemandSerializer,
        responses={201: PostDemandSerializer},
        tags=["OBS"],
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        serializer = CompleteDemandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity_demanded"]

        with transaction.atomic():
            demand = Demand.objects.select_for_update().get(pk=self.get_object().pk)
            if quantity > demand.quantity_todemand:
                raise DRFValidationError(
                    {
                        "quantity_demanded": (
                            "Demanded quantity cannot exceed pending quantity."
                        )
                    }
                )
            if (
                PostDemand.objects.filter(
                    demand_number=serializer.validated_data["demand_number"]
                )
                .exclude(spare=demand.spare)
                .exists()
            ):
                raise DRFValidationError(
                    {"demand_number": ("This demand number belongs to another spare.")}
                )
            post_demand = PostDemand.objects.create(
                spare=demand.spare,
                issue_entry=demand.issue_entry,
                quantity_demanded=quantity,
                demand_number=serializer.validated_data["demand_number"],
                demand_date=serializer.validated_data.get(
                    "demand_date",
                    timezone.now(),
                ),
                remarks=serializer.validated_data.get("remarks", ""),
                created_by=request.user.get_username(),
                created_by_user=request.user.CustomUser_profile,
                dart_number=demand.dart_number,
            )
            receive = Receive.objects.create(
                spare=demand.spare,
                issue_entry=demand.issue_entry,
                quantity_toreceive=quantity,
                demand_entry=post_demand,
                dart_number=demand.dart_number,
            )
            remaining_quantity = demand.quantity_todemand - quantity
            if remaining_quantity:
                demand.quantity_todemand = remaining_quantity
                demand.save(update_fields=["quantity_todemand"])
            else:
                demand.delete()

        return Response(
            {
                "post_demand": PostDemandSerializer(post_demand).data,
                "receive": ReceiveSerializer(receive).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def complete_from_payload(self, request):
        self.kwargs[self.lookup_url_kwarg or self.lookup_field] = payload_pk(
            request,
            "demand_id",
            "demand",
            "pk",
            "id",
        )
        return self.complete(request, pk=self.kwargs["pk"])


@tagged_viewset("OBS")
class PostDemandViewSet(CleanValidationModelViewSet):
    queryset = PostDemand.objects.select_related(
        "issue_entry",
        "spare",
        "created_by_user",
    ).all()
    serializer_class = PostDemandSerializer


@tagged_viewset("OBS")
class ReceiveViewSet(CleanValidationModelViewSet):
    queryset = Receive.objects.select_related(
        "demand_entry",
        "issue_entry",
        "spare",
    )
    serializer_class = ReceiveSerializer

    @extend_schema(
        request=CompleteReceiveSerializer,
        responses={201: PostReceiveSerializer},
        tags=["OBS"],
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        serializer = CompleteReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity_received"]
        if PostReceive.objects.filter(
            receipt_number=serializer.validated_data["receipt_number"]
        ).exists():
            raise DRFValidationError(
                {"receipt_number": "This receipt number already exists."}
            )

        with transaction.atomic():
            receive = Receive.objects.select_for_update().get(pk=self.get_object().pk)
            if quantity > receive.quantity_toreceive:
                raise DRFValidationError(
                    {
                        "quantity_received": (
                            "Received quantity cannot exceed pending quantity."
                        )
                    }
                )
            post_receive = PostReceive.objects.create(
                spare=receive.spare,
                issue_entry=receive.issue_entry,
                quantity_received=quantity,
                receipt_number=serializer.validated_data["receipt_number"],
                receive_date=serializer.validated_data.get(
                    "receive_date",
                    timezone.now(),
                ),
                nac_status=serializer.validated_data["nac_status"],
                remarks=serializer.validated_data.get("remarks", ""),
                dart_number=receive.dart_number,
                created_by=request.user.get_username(),
                created_by_user=request.user.CustomUser_profile,
            )
            remaining_quantity = receive.quantity_toreceive - quantity
            if remaining_quantity:
                receive.quantity_toreceive = remaining_quantity
                receive.save(update_fields=["quantity_toreceive"])
            else:
                receive.delete()

            issue_entries = (
                IssueList.objects.select_for_update()
                .filter(issue_entry__spare=post_receive.spare)
                .order_by("id")
            )
            quantity_to_adjust = quantity
            for issue_entry in issue_entries:
                if quantity_to_adjust >= issue_entry.quantity_toreturn:
                    quantity_to_adjust -= issue_entry.quantity_toreturn
                    issue_entry.delete()
                else:
                    issue_entry.quantity_toreturn -= quantity_to_adjust
                    issue_entry.save(update_fields=["quantity_toreturn"])
                    break

        return Response(
            {"post_receive": PostReceiveSerializer(post_receive).data},
            status=status.HTTP_201_CREATED,
        )


@tagged_viewset("OBS")
class PostReceiveViewSet(CleanValidationModelViewSet):
    queryset = PostReceive.objects.select_related(
        "issue_entry",
        "spare",
        "created_by_user",
    ).all()
    serializer_class = PostReceiveSerializer


@tagged_viewset("OBS")
class PlannedRoutineSpareListViewSet(CleanValidationModelViewSet):
    queryset = PlannedRoutineSpareList.objects.select_related(
        "planned_routine_description",
    ).all()
    serializer_class = PlannedRoutineSpareListSerializer

    @action(detail=False, methods=["get"])
    def requisition(self, request):
        planned_description_id = request.query_params.get("planned_routine_description")
        planned_spares = self.get_queryset().filter(is_deleted=False)
        if planned_description_id:
            planned_spares = planned_spares.filter(
                planned_routine_description_id=planned_description_id,
            )
        patterns = list(planned_spares.values_list("pattern_number", flat=True))
        onboard_by_pattern = {
            spare.pattern_number: spare
            for spare in Spares.objects.filter(pattern_number__in=patterns)
        }
        data = []
        for planned_spare in planned_spares:
            onboard_spare = onboard_by_pattern.get(planned_spare.pattern_number)
            data.append(
                {
                    "planned_spare_id": planned_spare.pk,
                    "pattern_number": planned_spare.pattern_number,
                    "quantity_required": planned_spare.quantity_required,
                    "onboard_spare": (onboard_spare.pk if onboard_spare else None),
                    "description": (onboard_spare.description if onboard_spare else ""),
                    "quantity_available": (
                        onboard_spare.quantity_available if onboard_spare else 0
                    ),
                    "available_onboard": bool(
                        onboard_spare
                        and onboard_spare.quantity_available
                        >= planned_spare.quantity_required
                    ),
                }
            )
        return Response(data)

    def _planned_obs_entries(self, pk):
        spare = Spares.objects.filter(pk=pk).first()
        if spare:
            return PlannedRoutineSpareList.objects.filter(
                pattern_number__iexact=spare.pattern_number
            )
        return PlannedRoutineSpareList.objects.filter(pk=pk)

    def _apply_requisition_change(self, request, *, soft_delete, defect):
        serializer = RequisitionDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pk = serializer.validated_data["pk"]
        inventory_type = serializer.validated_data["inventory_type"]

        if defect:
            model_map = {
                "OBS": DartSpare,
                "PIL": DartSpare,
                "WED": DartWedSpare,
                "MO": DartMOSpare,
            }
            queryset = model_map[inventory_type].objects.filter(pk=pk)
            if soft_delete:
                affected = queryset.update(is_delete=True)
            else:
                affected, _ = queryset.delete()
        elif inventory_type in {"OBS", "PIL"}:
            queryset = self._planned_obs_entries(pk)
            if soft_delete:
                affected = queryset.update(is_deleted=True)
            else:
                affected, _ = queryset.delete()
        else:
            model_map = {
                "WED": PlannedWEDSpareList,
                "MO": PlannedMOSpareList,
            }
            queryset = model_map[inventory_type].objects.filter(pk=pk)
            if soft_delete:
                affected = queryset.update(is_deleted=True)
            else:
                affected, _ = queryset.delete()

        if not affected:
            return Response(
                {
                    "success": False,
                    "error": "Requisition spare not found",
                    "affected": 0,
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True, "affected": affected})

    @action(detail=False, methods=["post"], url_path="delete-requisition-spare")
    def delete_requisition_spare(self, request):
        return self._apply_requisition_change(
            request,
            soft_delete=False,
            defect=False,
        )

    @action(detail=False, methods=["post"], url_path="delete-defect-requisition-spare")
    def delete_defect_requisition_spare(self, request):
        return self._apply_requisition_change(
            request,
            soft_delete=False,
            defect=True,
        )

    @action(detail=False, methods=["post"], url_path="soft-delete-after-cart")
    def soft_delete_after_cart(self, request):
        return self._apply_requisition_change(
            request,
            soft_delete=True,
            defect=False,
        )

    @action(detail=False, methods=["post"], url_path="soft-delete-after-cart-defect")
    def soft_delete_after_cart_defect(self, request):
        return self._apply_requisition_change(
            request,
            soft_delete=True,
            defect=True,
        )


@tagged_viewset("OBS")
class SparesMappingViewSet(CleanValidationModelViewSet):
    queryset = SparesMapping.objects.select_related(
        "equipment_class",
        "equipment",
        "section_name",
    ).all()
    serializer_class = SparesMappingSerializer


@tagged_viewset("OBS")
class NotInCattedItemViewSet(CleanValidationModelViewSet):
    queryset = NotInCattedItem.objects.select_related("spare_id").all()
    serializer_class = NotInCattedItemSerializer

    @action(detail=False, methods=["get"])
    def pending(self, request):
        queryset = self.get_queryset().filter(
            incatted_status=False,
            is_deleted=False,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"], url_path="mark-incatted")
    def mark_incatted(self, request, pk=None):
        item = self.get_object()
        item.incatted_status = True
        item.is_deleted = True
        item.save(update_fields=["incatted_status", "is_deleted"])
        return Response(self.get_serializer(item).data)


MISC_MASTER_DATA_MODELS = {
    "spare_class": (SpareClass, SpareClassSerializer),
    "denomination": (Denomination, DenominationSerializer),
    "equipment_class": (EquipmentClass, EquipmentClassSerializer),
    "authority": (Authority, AuthoritySerializer),
}


class MiscellaneousMasterDataView(APIView):
    """Create a SpareClass/Denomination/EquipmentClass/Authority entry by type."""

    def post(self, request):
        entry_type = request.data.get("type")
        config = MISC_MASTER_DATA_MODELS.get(entry_type)
        if not config:
            raise DRFValidationError(
                {"type": f"type must be one of {list(MISC_MASTER_DATA_MODELS)}."}
            )
        _, serializer_class = config
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EditMiscellaneousMasterDataView(APIView):
    """Rename a SpareClass/Denomination/EquipmentClass/Authority entry by type."""

    def post(self, request):
        entry_type = request.data.get("type")
        config = MISC_MASTER_DATA_MODELS.get(entry_type)
        if not config:
            raise DRFValidationError(
                {"type": f"type must be one of {list(MISC_MASTER_DATA_MODELS)}."}
            )
        model, serializer_class = config
        entry_id = request.data.get("id")
        if not entry_id:
            raise DRFValidationError({"id": "This field is required."})
        instance = model.objects.filter(pk=entry_id).first()
        if not instance:
            raise DRFValidationError({"id": "Entry not found."})
        serializer = serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
