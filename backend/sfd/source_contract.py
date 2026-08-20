# ruff: noqa: RUF012
from datetime import date, datetime, timedelta
from uuid import uuid4

import django_filters
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from master.models import Department, Ship, SubDepartment
from master.utils import get_this_ship
from users.models import CustomUserProfile

from .models import (
    ChangeEquipmentRequest,
    CompartmentMaster,
    Equipment,
    EquipmentCompartmentMapping,
    EquipmentType,
    RemoveEquipment,
    ReportExportJob,
    ShipEquipment,
    Supplier,
)


def _active_ship():
    return (
        get_this_ship() or Ship.objects.filter(active=1).first() or Ship.objects.first()
    )


def _ship_equipment_queryset():
    ship = _active_ship()
    if not ship:
        return ShipEquipment.objects.none()
    return ShipEquipment.objects.filter(ship_id=ship.id)


def _uid(prefix):
    return f"{prefix}-{uuid4().hex}"


def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class FrontendPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100
    alternate_page_size_query_params = ("limit", "entries_per_page")

    def get_page_size(self, request):
        page_size = super().get_page_size(request)
        if page_size is not None:
            return page_size

        for query_param in self.alternate_page_size_query_params:
            value = request.query_params.get(query_param)
            if value is None:
                continue
            try:
                page_size = int(value)
            except (TypeError, ValueError):
                return self.page_size
            return min(page_size, self.max_page_size)

        return self.page_size


def _paginated_response(request, rows):
    paginator = FrontendPageNumberPagination()
    page = paginator.paginate_queryset(list(rows), request)
    return paginator.get_paginated_response(page)


ACTIVITY_PERIOD_DAYS = {
    "today": 1,
    "week": 7,
    "month": 30,
    "quarter": 90,
    "year": 365,
}


def _build_activity_row(item, today):
    activity_date = item.updated_at or item.created_at
    activity_day = activity_date.date() if activity_date else today
    action = "Added"
    if item.updated_at and item.created_at and item.updated_at > item.created_at:
        action = "Updated"
    return {
        "d": max((today - activity_day).days, 0),
        "date": activity_day.strftime("%d %b %Y"),
        "equip": item.equipment_name
        or item.new_equipment_name
        or getattr(item.equipment, "equipment_code", None)
        or "Equipment",
        "action": action,
        "dept": getattr(item.department, "name", None) or "Unassigned",
        "ship": getattr(item.ship, "name", None) or "Ship",
        "status": "Verified" if item.active else "In Progress",
    }


def _fk_id(obj, field_name):
    return getattr(obj, f"{field_name}_id", None)


def _first_value(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _supplier_display(obj):
    if not obj:
        return None
    return _first_value(
        getattr(obj, "supplier_name", None),
        getattr(obj, "SupplierName", None),
    )


def _equipment_display(obj):
    if not obj:
        return None
    return _first_value(
        getattr(obj, "equipment_class", None),
        getattr(obj, "equipment_name", None),
        getattr(obj, "ilms_eq_code", None),
        getattr(obj, "equipment_code", None),
    )


def _sub_department_name(obj):
    cached = getattr(getattr(obj, "_state", None), "fields_cache", {}).get(
        "sub_department_f_key"
    )
    return _first_value(
        getattr(cached, "name", None),
        getattr(obj, "equipment_section", None),
        getattr(obj, "universal_id_m_sub_department", None),
    )


def _department_name(obj, dept_map):
    """dept_map only resolves rows whose own universal_id_m_department is set — some equipment
    (e.g. added through the CAT I/III forms rather than a CMMS sync) never gets that field filled
    in, even though its Sub Department was picked and that Sub Department already belongs to a
    Department. Falling back through sub_department_f_key.department_name covers exactly that
    case instead of just showing blank."""
    direct = dept_map.get(getattr(obj, "universal_id_m_department", None))
    if direct:
        return direct
    sub_dept = getattr(obj, "sub_department_f_key", None)
    return getattr(getattr(sub_dept, "department_name", None), "name", None) or ""


def _status_label(value):
    status_map = {
        1: "approved",
        2: "Pending",
        3: "Rejected",
        "1": "approved",
        "2": "Pending",
        "3": "Rejected",
    }
    return status_map.get(value, str(value) if value is not None else "")


def equipment_label(equipment_name, location_on_board):
    return f"{equipment_name} - {location_on_board or ''}".strip(" -")


def _resolve_date_filter(date_filter_value, date_field="created_at"):
    if not date_filter_value:
        return Q()
    now = timezone.now()
    clean_val = date_filter_value.lower().replace(" ", "_")
    if clean_val == "last_30_days":
        return Q(**{f"{date_field}__gte": now - timedelta(days=30)})
    if clean_val == "last_90_days":
        return Q(**{f"{date_field}__gte": now - timedelta(days=90)})
    if clean_val == "this_year":
        return Q(**{f"{date_field}__year": now.year})
    if clean_val == "last_year":
        return Q(**{f"{date_field}__year": now.year - 1})
    return Q()


def _filter_by_department(queryset, query_params):
    department_id = query_params.get("department") or query_params.get("department_id")
    if not department_id:
        return queryset
    try:
        department_id = int(department_id)
    except (TypeError, ValueError):
        return queryset.none()
    if not Department.objects.filter(id=department_id).exists():
        return queryset.none()
    return queryset.filter(department_id=department_id)


def _user_display_name(user):
    if not user:
        return "Unknown User"
    profile = getattr(user, "user_profile", None)
    rank_name = getattr(getattr(profile, "rank", None), "name", None) or "Captain"
    first = getattr(profile, "firstname", None) or "Yogesh"
    last = getattr(profile, "lastname", None) or "Chauhan"
    return f"{rank_name} {first} {last}"


class MessageModelViewSet(viewsets.ModelViewSet):
    pagination_class = FrontendPageNumberPagination
    create_message = "Record created successfully."
    update_message = "Record updated successfully."
    delete_message = "Record deleted successfully."

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": self.create_message, "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": self.update_message, "data": serializer.data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if hasattr(instance, "is_deleted"):
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted"])
        else:
            instance.delete()
        return Response({"message": self.delete_message})


class CompartmentSerializer(serializers.ModelSerializer):
    location_value = serializers.CharField(source="location", read_only=True)
    location_label = serializers.CharField(
        source="get_location_display", read_only=True
    )
    upper_deck_label = serializers.CharField(
        source="get_upper_deck_display", read_only=True
    )
    lower_deck_label = serializers.CharField(
        source="get_lower_deck_display", read_only=True
    )
    deck_no = serializers.SerializerMethodField()
    frame_station = serializers.SerializerMethodField()

    class Meta:
        model = CompartmentMaster
        fields = [
            "id",
            "name",
            "main_deck",
            "upper_deck",
            "upper_deck_label",
            "lower_deck",
            "lower_deck_label",
            "deck_no",
            "frame_station_from",
            "frame_station_to",
            "frame_station",
            "location",
            "location_value",
            "location_label",
        ]
        read_only_fields = ["id"]

    def get_deck_no(self, obj):
        if obj.main_deck:
            return "Main Deck"
        return obj.get_upper_deck_display() or obj.get_lower_deck_display() or ""

    def get_frame_station(self, obj):
        if obj.frame_station_from is None or obj.frame_station_to is None:
            return ""
        if obj.frame_station_from == obj.frame_station_to:
            return str(obj.frame_station_from)
        return f"{obj.frame_station_from} - {obj.frame_station_to}"

    def validate(self, attrs):
        name = attrs.get("name", getattr(self.instance, "name", None))
        self._validate_unique_name(name)

        frame_from = attrs.get(
            "frame_station_from", getattr(self.instance, "frame_station_from", None)
        )
        frame_to = attrs.get(
            "frame_station_to", getattr(self.instance, "frame_station_to", None)
        )
        if frame_from is not None and frame_to is not None and frame_from > frame_to:
            raise serializers.ValidationError(
                "Frame station from cannot be greater than frame station to."
            )
        return attrs

    def validate_name(self, value):
        name = value.strip() if value else ""
        if not name:
            raise serializers.ValidationError("Compartment name is required.")
        return name

    def _validate_unique_name(self, name):
        queryset = CompartmentMaster.objects.filter(is_deleted=False, name__iexact=name)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                {"name": "Compartment with this name already exists."}
            )


def _choice_filter_values(choices, raw_value):
    value = str(raw_value or "").strip()
    if not value:
        return []

    matches = []
    value_lower = value.lower()
    for choice_value, choice_label in choices:
        choice_value = str(choice_value)
        choice_label = str(choice_label)
        if value_lower in {choice_value.lower(), choice_label.lower()}:
            matches.append(choice_value)

    return matches or [value]


class CompartmentFilter(django_filters.FilterSet):
    main_deck = django_filters.BooleanFilter(field_name="main_deck")
    upper_deck = django_filters.CharFilter(method="filter_upper_deck")
    lower_deck = django_filters.CharFilter(method="filter_lower_deck")
    location = django_filters.CharFilter(method="filter_location")
    frame_station = django_filters.NumberFilter(method="filter_frame_station")

    class Meta:
        model = CompartmentMaster
        fields = ["main_deck", "upper_deck", "lower_deck", "location", "frame_station"]

    def filter_frame_station(self, queryset, name, value):
        return queryset.filter(
            frame_station_from__lte=value, frame_station_to__gte=value
        )

    def filter_upper_deck(self, queryset, name, value):
        return queryset.filter(
            upper_deck__in=_choice_filter_values(
                CompartmentMaster.UpperDeck.choices, value
            )
        )

    def filter_lower_deck(self, queryset, name, value):
        return queryset.filter(
            lower_deck__in=_choice_filter_values(
                CompartmentMaster.LowerDeck.choices, value
            )
        )

    def filter_location(self, queryset, name, value):
        return queryset.filter(
            location__in=_choice_filter_values(
                CompartmentMaster.Location.choices, value
            )
        )


class SubDepartmentContractSerializer(serializers.ModelSerializer):
    department = serializers.IntegerField(source="department_name_id")
    department_name = serializers.CharField(
        source="department_name.name", read_only=True
    )
    department_code = serializers.CharField(
        source="department_name.code", read_only=True
    )

    class Meta:
        model = SubDepartment
        fields = [
            "id",
            "department",
            "department_name",
            "department_code",
            "name",
            "code",
            "equipment_count",
            "active",
        ]
        read_only_fields = ["id", "department_name", "department_code"]
        extra_kwargs = {
            "active": {"required": False},
            "equipment_count": {"required": False},
        }

    def validate(self, attrs):
        department_id = attrs.get(
            "department_name_id", getattr(self.instance, "department_name_id", None)
        )
        name = attrs.get("name", getattr(self.instance, "name", None))
        self._validate_unique_name(department_id, name)
        return attrs

    def validate_name(self, value):
        name = value.strip() if value else ""
        if not name:
            raise serializers.ValidationError("Sub-department name is required.")
        return name

    def validate_code(self, value):
        return value.strip() if value else value

    def _validate_unique_name(self, department_id, name):
        queryset = SubDepartment.objects.filter(
            is_deleted=False,
            department_name_id=department_id,
            name__iexact=name,
        )
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                {
                    "name": (
                        "Sub-department with this name already exists for "
                        "selected department."
                    )
                }
            )

    def create(self, validated_data):
        validated_data.setdefault("active", True)
        validated_data.setdefault("equipment_count", 0)
        validated_data.setdefault("universal_id_m_sub_department", _uid("sub-dept"))
        return super().create(validated_data)


class SubDepartmentFilter(django_filters.FilterSet):
    department = django_filters.NumberFilter(method="filter_department")
    active = django_filters.BooleanFilter(field_name="active")
    equipment_count = django_filters.NumberFilter(method="filter_equipment_count")

    class Meta:
        model = SubDepartment
        fields = ["department", "active", "equipment_count"]

    def filter_department(self, queryset, name, value):
        department = self.request.query_params.get(
            "department"
        ) or self.request.query_params.get("department_id")
        return queryset.filter(department_name_id=department)

    def filter_equipment_count(self, queryset, name, value):
        equipment_count = self.request.query_params.get(
            "equipment_count"
        ) or self.request.query_params.get("min_equipment_count")
        return queryset.filter(equipment_count=equipment_count)


class SourceShipEquipmentSerializer(serializers.ModelSerializer):
    serial_no = serializers.CharField(
        source="equipment_serial_no", required=False, allow_blank=True, allow_null=True
    )
    equipment_sr_no = serializers.CharField(
        source="equipment_serial_no", read_only=True
    )
    deck_no = serializers.CharField(
        source="deck", required=False, allow_blank=True, allow_null=True
    )
    frame_station = serializers.CharField(
        source="frame", required=False, allow_blank=True, allow_null=True
    )
    shell_life = serializers.CharField(
        source="service_life", required=False, allow_blank=True, allow_null=True
    )
    qty_fitted = serializers.IntegerField(source="no_of_fits", required=False)
    location = serializers.CharField(
        source="location_code", required=False, allow_blank=True, allow_null=True
    )
    compartment_name = serializers.CharField(
        source="location_on_board", required=False, allow_blank=True, allow_null=True
    )
    rh_at_installation = serializers.CharField(
        source="rshi", required=False, allow_blank=True, allow_null=True
    )
    insma_code = serializers.CharField(
        source="equipment.equipment_code", read_only=True
    )
    equipment_master_name = serializers.SerializerMethodField()
    supplier_name = serializers.SerializerMethodField()
    manufacturer_name = serializers.SerializerMethodField()
    sub_dept = serializers.SerializerMethodField()

    class Meta:
        model = ShipEquipment
        fields = [
            "id",
            "type",
            "category",
            "equipment",
            "system",
            "ship",
            "supplier",
            "manufacturer",
            "equipment_model",
            "equipment_name",
            "new_equipment_name",
            "new_system_name",
            "nomenclature",
            "new_nomenclature",
            "oem_part_no",
            "new_oem_part_no",
            "serial_no",
            "equipment_sr_no",
            "new_equipment_sr_no",
            "deck_no",
            "frame_station",
            "location",
            "location_code",
            "compartment_name",
            "location_on_board",
            "installation_date",
            "new_installation_date",
            "removal_date",
            "authority_date",
            "authority_of_installation",
            "authority_of_removal",
            "qty_fitted",
            "no_of_fits",
            "shell_life",
            "service_life",
            "rh_at_installation",
            "rshi",
            "equipment_section",
            "sub_department_f_key",
            "status",
            "active",
            "is_system",
            "mapping_status",
            "mapped_to",
            "mapped_at",
            "maintop_id",
            "universal_id_t_equipment_ship_detail",
            "universal_id_m_equipment",
            "universal_id_m_supplier",
            "universal_id_m_manufacturer",
            "universal_id_m_equipment_parent",
            "universal_id_m_sub_department",
            "insma_code",
            "equipment_master_name",
            "supplier_name",
            "manufacturer_name",
            "sub_dept",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_equipment_master_name(self, obj):
        return (
            getattr(obj.equipment, "equipment_name", None)
            or obj.equipment_name
            or getattr(obj.equipment, "ilms_eq_code", None)
        )

    def get_supplier_name(self, obj):
        return getattr(obj.supplier, "SupplierName", None) or getattr(
            obj.supplier, "supplier_name", None
        )

    def get_manufacturer_name(self, obj):
        return getattr(obj.manufacturer, "SupplierName", None) or getattr(
            obj.manufacturer, "supplier_name", None
        )

    def get_sub_dept(self, obj):
        return _sub_department_name(obj)

    def to_representation(self, obj):
        equipment = getattr(obj, "equipment", None)
        supplier = getattr(obj, "supplier", None)
        manufacturer = getattr(obj, "manufacturer", None)
        parent_equipment = getattr(obj, "parent_equipment", None)
        parent_equipment_id = (
            getattr(parent_equipment, "pk", None)
            if parent_equipment is not None
            else None
        )

        return {
            "created_at": getattr(obj, "created_at", None),
            "updated_at": getattr(obj, "updated_at", None),
            "created_by": _fk_id(obj, "created_by"),
            "updated_by": None,
            "equipment_ship_id": getattr(obj, "pk", None),
            "equipment": _fk_id(obj, "equipment"),
            "equipment_code": getattr(equipment, "equipment_code", None),
            "equipment_name": _first_value(
                getattr(obj, "equipment_name", None),
                getattr(equipment, "equipment_class", None),
                getattr(equipment, "equipment_code", None),
            ),
            "new_equipment_name": getattr(obj, "new_equipment_name", None),
            "system": _fk_id(obj, "system"),
            "new_system_name": getattr(obj, "new_system_name", None),
            "ship": _fk_id(obj, "ship"),
            "equipment_model": _first_value(
                getattr(obj, "equipment_model", None),
                getattr(equipment, "model", None),
            ),
            "location_code": getattr(obj, "location_code", None),
            "location_on_board": getattr(obj, "location_on_board", None),
            "no_of_fits": getattr(obj, "no_of_fits", None),
            "equipment_sr_no": getattr(obj, "equipment_serial_no", None),
            "new_equipment_sr_no": getattr(obj, "new_equipment_sr_no", None),
            "oem_part_no": getattr(obj, "oem_part_no", None),
            "new_oem_part_no": getattr(obj, "new_oem_part_no", None),
            "deck_no": getattr(obj, "deck", None),
            "installation_date": getattr(obj, "installation_date", None),
            "new_installation_date": getattr(obj, "new_installation_date", None),
            "removal_date": getattr(obj, "removal_date", None),
            "supplier": _fk_id(obj, "supplier"),
            "supplier_name": _first_value(
                self.get_supplier_name(obj),
                getattr(obj, "new_supplier_name", None),
            ),
            "new_supplier_name": getattr(obj, "new_supplier_name", None),
            "manufacturer": _fk_id(obj, "manufacturer"),
            "manufacturer_name": _first_value(
                self.get_manufacturer_name(obj),
                getattr(obj, "new_manufacturer_name", None),
            ),
            "new_manufacturer_name": getattr(obj, "new_manufacturer_name", None),
            "remark": _first_value(
                getattr(obj, "remark", None),
                getattr(obj, "remarks", None),
            ),
            "srar_applicable": getattr(obj, "is_srar", None),
            "maintop_id": getattr(obj, "maintop_id", None),
            "parent_equipment": parent_equipment_id,
            "active": getattr(obj, "active", None),
            "is_system": getattr(obj, "is_system", None),
            "mapped_to": getattr(obj, "mapped_to", None),
            "mapped_at": getattr(obj, "mapped_at", None),
            "mapping_status": getattr(obj, "mapping_status", None),
            "nomenclature": getattr(obj, "nomenclature", None),
            "new_nomenclature": getattr(obj, "new_nomenclature", None),
            "service_life": getattr(obj, "service_life", None),
            "new_service_life": getattr(obj, "new_service_life", None),
            "status": getattr(obj, "status", None),
            "equipment_type": _fk_id(obj, "equipment_type_f_key"),
            "removal_remark": _first_value(
                getattr(obj, "removal_remark", None),
                getattr(obj, "removal_remarks", None),
            ),
            "authority_of_removal": _first_value(
                getattr(obj, "authority_of_removal", None),
                getattr(obj, "authority_removal", None),
            ),
            "authority_of_installation": _first_value(
                getattr(obj, "authority_of_installation", None),
                getattr(obj, "authority_installation", None),
            ),
            "rh_at_installation": _first_value(
                getattr(obj, "rshi", None),
                getattr(obj, "eq_rhsi", None),
            ),
            "insma_remarks": getattr(obj, "insma_remarks", None),
            "universal_id_t_equipment_ship_detail": _first_value(
                getattr(obj, "universal_id_t_equipment_ship_detail", None),
                getattr(obj, "universal_id_t_ship_detail", None),
            ),
            "universal_id_m_ship": getattr(obj, "universal_id_m_ship", None),
            "universal_id_m_equipment": _first_value(
                getattr(obj, "universal_id_m_equipment", None),
                getattr(equipment, "universal_id_m_equipment", None),
            ),
            "universal_id_m_srar_type": getattr(obj, "universal_id_m_srar_type", None),
            "universal_id_m_supplier": _first_value(
                getattr(obj, "universal_id_m_supplier", None),
                getattr(supplier, "Universal_ID_M_Supplier", None),
            ),
            "universal_id_m_manufacturer": _first_value(
                getattr(obj, "universal_id_m_manufacturer", None),
                getattr(manufacturer, "Universal_ID_M_Supplier", None),
            ),
            "universal_id_m_equipment_parent": getattr(
                obj, "universal_id_m_equipment_parent", None
            ),
            "universal_id_m_department": getattr(
                obj, "universal_id_m_department", None
            ),
            "universal_id_t_maintop_header": getattr(
                obj, "universal_id_t_maintop_header", None
            ),
            "universal_id_ch_master_equipment_type": getattr(
                obj, "universal_id_ch_master_equipment_type", None
            ),
            "universal_id_m_sub_department": getattr(
                obj, "universal_id_m_sub_department", None
            ),
            "is_synced": getattr(obj, "is_synced", None),
            "type": getattr(obj, "type", None),
            "category": getattr(obj, "category", None),
            "frame_station": getattr(obj, "frame", None),
            "equipment_section": _fk_id(obj, "sub_department_f_key"),
        }

    def create(self, validated_data):
        validated_data.setdefault("ship", _active_ship())
        validated_data.setdefault("type", ShipEquipment.TransactionType.EQUIPMENT)
        validated_data.setdefault("category", ShipEquipment.TransactionCategory.CAT1)
        validated_data.setdefault("active", True)
        validated_data.setdefault("status", "1")
        validated_data.setdefault("universal_id_t_equipment_ship_detail", _uid("SFD"))
        if (
            self.context.get("request")
            and self.context["request"].user.is_authenticated
        ):
            validated_data.setdefault(
                "created_by",
                getattr(self.context["request"].user, "user_profile", None),
            )
        obj = super().create(validated_data)
        return obj


class EquipmentCompartmentMappingSerializer(serializers.ModelSerializer):
    equipment_name = serializers.SerializerMethodField()
    compartment_name = serializers.CharField(source="compartment.name", read_only=True)

    class Meta:
        model = EquipmentCompartmentMapping
        fields = [
            "id",
            "equipment",
            "equipment_name",
            "compartment",
            "compartment_name",
            "created_at",
        ]

    def get_equipment_name(self, obj):
        return (
            obj.equipment.equipment_name
            or obj.equipment.ilms_eq_code
            or obj.equipment.equipment_code
        )

    def create(self, validated_data):
        user = self.context.get("request").user if self.context.get("request") else None
        if user and user.is_authenticated:
            validated_data["created_by"] = getattr(user, "user_profile", None)
        return super().create(validated_data)


class RemoveEquipmentContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoveEquipment
        fields = "__all__"


def _get_master_equipment(universal_id):
    if not universal_id:
        return None
    return Equipment.objects.filter(universal_id_m_equipment=universal_id).first()


def _get_master_supplier(universal_id):
    if not universal_id:
        return None
    return Supplier.objects.filter(Universal_ID_M_Supplier=universal_id).first()


@transaction.atomic
def _create_sfd_transaction(validated_data):
    category = validated_data["category"]
    for key in (
        "equipment_name",
        "system_name",
        "manufacturer_name",
        "supplier_name",
        "new_oem_name",
        "new_serial_no",
    ):
        validated_data.pop(key, None)
    user = validated_data.pop("user", None)
    validated_data.setdefault("universal_id_t_equipment_ship_detail", _uid("SFD"))
    validated_data.setdefault("ship", _active_ship())
    validated_data["is_synced"] = True
    if user and getattr(user, "is_authenticated", False):
        validated_data["created_by"] = getattr(user, "user_profile", None)
    display_name = _user_display_name(user)

    tx = ShipEquipment.objects.create(**validated_data)

    # A new Equipment-type transaction with a picked "System Name" gets mapped to that system
    # automatically — whether the equipment was already mapped (frontend locks System Name to the
    # existing mapping in that case, so this just carries it forward onto the new row) or being
    # mapped for the first time (frontend leaves System Name open for a normal pick). Mirrors
    # EquipmentSystemMapAPIView's own equipment/system linking exactly.
    system_catalog_uid = validated_data.get("universal_id_m_equipment_parent")
    if tx.type == ShipEquipment.TransactionType.EQUIPMENT and system_catalog_uid:
        system_row = (
            ShipEquipment.objects.filter(universal_id_m_equipment=system_catalog_uid)
            .exclude(pk=tx.pk)
            .first()
        )
        if system_row:
            tx.mapped_to = system_row.universal_id_t_equipment_ship_detail
            tx.mapping_status = ShipEquipment.MappingStatus.MAPPED
            tx.mapped_at = timezone.now()
            tx.save(update_fields=["mapped_to", "mapping_status", "mapped_at"])
            system_row.is_system = True
            system_row.save(update_fields=["is_system"])

    if category in (
        ShipEquipment.TransactionCategory.CAT1,
        ShipEquipment.TransactionCategory.CAT2,
        ShipEquipment.TransactionCategory.CAT3,
    ):
        ChangeEquipmentRequest.objects.create(
            equipment=tx.equipment or Equipment.objects.first(),
            ship_equipment=tx,
            removal_remark="",
            new_serial=tx.equipment_model,
            is_synced=0,
            universal_id_t_sfd_change_request=_uid("SFDCR"),
            universal_id_a_user_created_by=display_name,
        )
    elif category == ShipEquipment.TransactionCategory.SURVEY:
        RemoveEquipment.objects.create(
            equipment=tx.equipment or Equipment.objects.first(),
            ship_equipment=tx,
            removal_remark="",
            removal_date=tx.removal_date,
            authority_of_removal=tx.authority_of_removal,
            equipment_serial_no=tx.equipment_serial_no,
            request_type=2,
            installation_date=tx.new_installation_date,
            installation_remark="",
            is_synced=0,
            approved_reject=3,
        )

    return tx


@transaction.atomic
def _update_sfd_transaction(instance, validated_data):
    category = instance.category
    user = validated_data.pop("user", None)
    for key in (
        "equipment_name",
        "system_name",
        "manufacturer_name",
        "supplier_name",
        "new_oem_name",
        "new_serial_no",
    ):
        validated_data.pop(key, None)

    for field, value in validated_data.items():
        setattr(instance, field, value)
    instance.save()

    display_name = _user_display_name(user)

    if category in (
        ShipEquipment.TransactionCategory.CAT1,
        ShipEquipment.TransactionCategory.CAT2,
        ShipEquipment.TransactionCategory.CAT3,
    ):
        change_request = ChangeEquipmentRequest.objects.filter(
            ship_equipment=instance
        ).first()
        if change_request:
            change_request.new_serial = instance.equipment_model
            change_request.universal_id_a_user_created_by = display_name
            change_request.save(
                update_fields=["new_serial", "universal_id_a_user_created_by"]
            )
    elif category == ShipEquipment.TransactionCategory.SURVEY:
        remove_request = RemoveEquipment.objects.filter(ship_equipment=instance).first()
        if remove_request:
            remove_request.removal_date = instance.removal_date
            remove_request.authority_of_removal = instance.authority_of_removal
            remove_request.equipment_serial_no = instance.equipment_serial_no
            remove_request.installation_date = instance.new_installation_date
            remove_request.save(
                update_fields=[
                    "removal_date",
                    "authority_of_removal",
                    "equipment_serial_no",
                    "installation_date",
                ]
            )

    return instance


class SFDTransactionBaseContractSerializer(serializers.ModelSerializer):
    expected_category = None
    type = serializers.ChoiceField(
        choices=ShipEquipment.TransactionType.choices,
        help_text="Transaction type: equipment or system.",
    )
    category = serializers.ChoiceField(
        choices=ShipEquipment.TransactionCategory.choices,
        help_text="Transaction category: CAT1, CAT2, CAT3, SURVEY, or OTHER.",
    )
    equipment_universal_id = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Universal ID for the selected equipment.",
    )
    system_universal_id = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Universal ID for the selected system.",
    )
    model_universal_id = serializers.CharField(write_only=True, help_text="Model name.")
    nomenclature = serializers.CharField(help_text="Equipment nomenclature.")
    supplier_universal_id = serializers.CharField(
        write_only=True, help_text="Universal ID for the selected supplier."
    )
    manufacturer_universal_id = serializers.CharField(
        write_only=True, help_text="Universal ID for the selected manufacturer."
    )
    serial_no = serializers.CharField(
        source="equipment_serial_no", help_text="Equipment serial number."
    )
    deck_no = serializers.CharField(source="deck", help_text="Deck number.")
    location = serializers.ChoiceField(
        source="location_code",
        choices=ShipEquipment.Location.choices,
        help_text="Location code on board.",
    )
    compartment_name = serializers.CharField(
        source="location_on_board",
        help_text="Location on board or compartment name.",
    )
    frame_station_from = serializers.CharField(
        write_only=True, help_text="Starting frame station value."
    )
    frame_station_to = serializers.CharField(
        write_only=True, help_text="Ending frame station value."
    )
    frame_station = serializers.CharField(source="frame", read_only=True)
    installation_date = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Installation date and time."
    )
    authority_of_installation = serializers.CharField(
        allow_blank=True, help_text="Authority of installation."
    )
    authority_date = serializers.DateField(
        required=False, allow_null=True, help_text="Date of Authority Given."
    )
    qty_fitted = serializers.IntegerField(
        source="no_of_fits", help_text="Quantity fitted."
    )
    shell_life = serializers.IntegerField(
        source="service_life", help_text="Service life or shelf life."
    )
    rh_at_installation = serializers.CharField(
        source="rshi", required=False, allow_blank=True, allow_null=True
    )
    equipment_section = serializers.CharField(help_text="Equipment section code.")

    def create(self, validated_data):
        request = self.context["request"]
        from_station = validated_data.pop("frame_station_from", None)
        to_station = validated_data.pop("frame_station_to", None)
        ids = self._pop_lookup_fields(validated_data)
        validated_data.update({"active": True, "status": "1", "user": request.user})
        self._populate_equipment_fields(validated_data, ids)
        self._populate_master_fields(validated_data, ids)
        self._set_frame_station(validated_data, from_station, to_station)
        return _create_sfd_transaction(validated_data)

    def update(self, instance, validated_data):
        request = self.context["request"]
        from_station = validated_data.pop("frame_station_from", None)
        to_station = validated_data.pop("frame_station_to", None)
        ids = self._pop_lookup_fields(validated_data)
        validated_data["user"] = request.user.CustomUser_profile
        self._populate_equipment_fields(validated_data, ids)
        self._populate_master_fields(validated_data, ids)
        self._set_frame_station(validated_data, from_station, to_station)
        return _update_sfd_transaction(instance, validated_data)

    def _pop_lookup_fields(self, validated_data):
        return {
            "equipment": validated_data.pop("equipment_universal_id", None),
            "system": validated_data.pop("system_universal_id", None),
            "model": validated_data.pop("model_universal_id", None),
            "supplier": validated_data.pop("supplier_universal_id", None),
            "manufacturer": validated_data.pop("manufacturer_universal_id", None),
            "section": validated_data.pop("equipment_section", None),
        }

    def _populate_equipment_fields(self, validated_data, ids):
        txn_type = validated_data["type"]
        equipment = _get_master_equipment(ids["equipment"])
        system = _get_master_equipment(ids["system"])

        if equipment and txn_type == ShipEquipment.TransactionType.EQUIPMENT:
            validated_data["equipment"] = equipment
            validated_data["universal_id_m_equipment"] = ids["equipment"]

        if system:
            validated_data["system"] = system
            validated_data["universal_id_m_equipment_parent"] = ids["system"]
            validated_data["parent_equipment"] = system

    def _populate_master_fields(self, validated_data, ids):
        model = _get_master_equipment(ids["model"])
        if model:
            validated_data["equipment_model"] = getattr(
                model, "equipment_model", None
            ) or getattr(model, "model", None)

        supplier = _get_master_supplier(ids["supplier"])
        if supplier:
            validated_data["supplier"] = supplier
            validated_data["universal_id_m_supplier"] = ids["supplier"]

        manufacturer = _get_master_supplier(ids["manufacturer"])
        if manufacturer:
            validated_data["manufacturer"] = manufacturer
            validated_data["universal_id_m_manufacturer"] = ids["manufacturer"]

        if ids["section"]:
            section = SubDepartment.objects.filter(code=ids["section"]).first()
            if section:
                validated_data["sub_department_f_key"] = section
                validated_data["equipment_section"] = section.code
                validated_data["universal_id_m_sub_department"] = (
                    section.universal_id_m_sub_department
                )
            else:
                validated_data["equipment_section"] = ids["section"]

    def _set_frame_station(self, validated_data, start, end):
        if start or end:
            validated_data["frame"] = f"{start or ''} - {end or ''}".strip(" -")

    class Meta:
        model = ShipEquipment
        fields = [
            "type",
            "category",
            "equipment_universal_id",
            "system_universal_id",
            "model_universal_id",
            "nomenclature",
            "manufacturer_universal_id",
            "supplier_universal_id",
            "oem_part_no",
            "serial_no",
            "deck_no",
            "location",
            "compartment_name",
            "frame_station_from",
            "frame_station_to",
            "frame_station",
            "installation_date",
            "authority_of_installation",
            "authority_date",
            "qty_fitted",
            "shell_life",
            "rh_at_installation",
            "equipment_section",
        ]


REQUIRED_CAT1 = "Required for CAT1."
REQUIRED_CAT2 = "Required for CAT2."
REQUIRED_CAT3 = "Required for CAT3."
REQUIRED_SURVEY_DEMAND = "Required for Survey & Demand."
REQUIRED_OTHERS = "Required for Others."
QTY_FITTED_ERROR = "Qty Fitted should be grater than 0"
SHELL_LIFE_ERROR = "Shell Life should be grater than 0"
CATEGORY_ERROR = "Please Check Transaction Category."
TYPE_ERROR = "Please Check Transaction Type."
INVALID_FUTURE_DATE = "Installation Date cannot be a future date."


def _local_date(value):
    """DateTimeField gives back an aware datetime; compare calendar dates in local time."""
    if isinstance(value, datetime):
        return (timezone.localtime(value) if timezone.is_aware(value) else value).date()
    return value


def _validate_common(attrs, required_fields, error_message, expected_category):
    for field in required_fields:
        if not attrs.get(field):
            raise serializers.ValidationError({field: error_message})

    validations = {
        "qty_fitted": (attrs["no_of_fits"] > 0, QTY_FITTED_ERROR),
        "shell_life": (int(attrs["service_life"]) > 0, SHELL_LIFE_ERROR),
        "installation_date": (
            _local_date(attrs["installation_date"]) <= timezone.localdate(),
            INVALID_FUTURE_DATE,
        ),
    }
    for field, (is_valid, error) in validations.items():
        if not is_valid:
            raise serializers.ValidationError({field: error})

    if attrs["type"] not in {
        ShipEquipment.TransactionType.EQUIPMENT,
        ShipEquipment.TransactionType.SYSTEM,
    }:
        raise serializers.ValidationError({"type": TYPE_ERROR})

    if attrs["category"] != expected_category:
        raise serializers.ValidationError({"category": CATEGORY_ERROR})

    if attrs["type"] == ShipEquipment.TransactionType.EQUIPMENT:
        required = ("equipment_universal_id", "system_universal_id")
    else:
        required = ("system_universal_id",)
    for field in required:
        if not attrs.get(field):
            raise serializers.ValidationError({field: error_message})


class CAT1Serializer(SFDTransactionBaseContractSerializer):
    expected_category = ShipEquipment.TransactionCategory.CAT1

    def validate(self, attrs):
        required_fields = (
            "type",
            "category",
            "model_universal_id",
            "nomenclature",
            "supplier_universal_id",
            "manufacturer_universal_id",
            "oem_part_no",
            "equipment_serial_no",
            "location_on_board",
            "deck",
            "frame_station_from",
            "frame_station_to",
            "location_code",
            "installation_date",
            "authority_of_installation",
            "authority_date",
            "no_of_fits",
            "service_life",
            "equipment_section",
        )
        _validate_common(attrs, required_fields, REQUIRED_CAT1, self.expected_category)
        return attrs

    class Meta(SFDTransactionBaseContractSerializer.Meta):
        fields = SFDTransactionBaseContractSerializer.Meta.fields


class CAT2Serializer(SFDTransactionBaseContractSerializer):
    expected_category = ShipEquipment.TransactionCategory.CAT2

    def validate(self, attrs):
        required_fields = (
            "type",
            "category",
            "model_universal_id",
            "nomenclature",
            "supplier_universal_id",
            "manufacturer_universal_id",
            "oem_part_no",
            "equipment_serial_no",
            "location_on_board",
            "deck",
            "frame_station_from",
            "frame_station_to",
            "location_code",
            "installation_date",
            "authority_of_installation",
            "authority_date",
            "no_of_fits",
            "service_life",
            "equipment_section",
        )
        _validate_common(attrs, required_fields, REQUIRED_CAT2, self.expected_category)
        return attrs

    class Meta(SFDTransactionBaseContractSerializer.Meta):
        fields = SFDTransactionBaseContractSerializer.Meta.fields


class CAT3Serializer(SFDTransactionBaseContractSerializer):
    expected_category = ShipEquipment.TransactionCategory.CAT3
    new_equipment_name = serializers.CharField(
        help_text="New equipment name for CAT3 transactions."
    )
    new_system_name = serializers.CharField(
        allow_blank=True, help_text="New system name for CAT3 transactions."
    )
    new_nomenclature = serializers.CharField(
        help_text="New nomenclature for CAT3 transactions."
    )
    new_oem_name = serializers.CharField(
        write_only=True, help_text="New OEM name for CAT3 transactions."
    )
    new_supplier_name = serializers.CharField(
        help_text="New supplier name for CAT3 transactions."
    )
    new_oem_part_no = serializers.CharField(
        help_text="New OEM part number for CAT3 transactions."
    )
    new_serial_no = serializers.CharField(
        write_only=True, help_text="New serial number for CAT3 transactions."
    )

    def validate(self, attrs):
        required_fields = [
            "type",
            "category",
            "model_universal_id",
            "new_nomenclature",
            "supplier_universal_id",
            "manufacturer_universal_id",
            "new_oem_name",
            "new_supplier_name",
            "new_oem_part_no",
            "new_serial_no",
            "location_on_board",
            "deck",
            "frame_station_from",
            "frame_station_to",
            "location_code",
            "installation_date",
            "authority_of_installation",
            "authority_date",
            "no_of_fits",
            "service_life",
            "equipment_section",
        ]
        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError({field: REQUIRED_CAT3})

        validations = {
            "qty_fitted": (attrs["no_of_fits"] > 0, QTY_FITTED_ERROR),
            "shell_life": (int(attrs["service_life"]) > 0, SHELL_LIFE_ERROR),
            "installation_date": (
                _local_date(attrs["installation_date"]) <= timezone.localdate(),
                INVALID_FUTURE_DATE,
            ),
        }
        for field, (is_valid, error) in validations.items():
            if not is_valid:
                raise serializers.ValidationError({field: error})

        if attrs["type"] not in {
            ShipEquipment.TransactionType.EQUIPMENT,
            ShipEquipment.TransactionType.SYSTEM,
        }:
            raise serializers.ValidationError({"type": TYPE_ERROR})
        if attrs["category"] != self.expected_category:
            raise serializers.ValidationError({"category": CATEGORY_ERROR})

        if attrs["type"] == ShipEquipment.TransactionType.EQUIPMENT:
            required = ("new_equipment_name", "new_system_name")
        else:
            required = ("new_system_name",)
        for field in required:
            if not attrs.get(field):
                raise serializers.ValidationError({field: REQUIRED_CAT3})
        return attrs

    class Meta(SFDTransactionBaseContractSerializer.Meta):
        fields = SFDTransactionBaseContractSerializer.Meta.fields + [
            "new_equipment_name",
            "new_system_name",
            "new_nomenclature",
            "new_oem_name",
            "new_supplier_name",
            "new_oem_part_no",
            "new_serial_no",
        ]


class SurveySerializer(SFDTransactionBaseContractSerializer):
    expected_category = ShipEquipment.TransactionCategory.SURVEY
    removal_date = serializers.DateTimeField(
        help_text="Removal date and time for Survey & Demand transactions."
    )
    authority_of_removal = serializers.CharField(
        help_text="Authority for removal on Survey & Demand transactions."
    )
    new_installation_date = serializers.DateTimeField(
        help_text="New installation date and time for Survey & Demand transactions."
    )
    new_serial_no = serializers.CharField(
        source="new_equipment_sr_no",
        help_text="New serial number for Survey & Demand transactions.",
    )
    installation_remark = serializers.CharField(
        source="installation_remarks",
        help_text="Installation Remark for Survey & Demand transactions.",
    )
    new_service_life = serializers.IntegerField(
        help_text="New Shelf Life for Survey & Demand transactions."
    )

    def validate(self, attrs):
        required_fields = [
            "type",
            "category",
            "model_universal_id",
            "nomenclature",
            "supplier_universal_id",
            "manufacturer_universal_id",
            "oem_part_no",
            "equipment_serial_no",
            "removal_date",
            "authority_of_removal",
            "new_equipment_sr_no",
            "new_installation_date",
            "service_life",
            "authority_of_installation",
            "authority_date",
            "no_of_fits",
            "installation_remarks",
            "new_service_life",
        ]
        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError({field: REQUIRED_SURVEY_DEMAND})

        validations = {
            "qty_fitted": (attrs["no_of_fits"] > 0, QTY_FITTED_ERROR),
            "shell_life": (int(attrs["service_life"]) > 0, SHELL_LIFE_ERROR),
            "new_shell_life": (attrs["new_service_life"] > 0, SHELL_LIFE_ERROR),
            "removal_date": (
                attrs["removal_date"] > attrs["installation_date"],
                "Removal Date Should be Ahead of Installation Date",
            ),
            "new_installation_date": (
                attrs["new_installation_date"] > attrs["removal_date"],
                "New Installation Date Should be Ahead of Removal Date",
            ),
        }
        for field, (is_valid, error) in validations.items():
            if not is_valid:
                raise serializers.ValidationError({field: error})

        if attrs["type"] not in {
            ShipEquipment.TransactionType.EQUIPMENT,
            ShipEquipment.TransactionType.SYSTEM,
        }:
            raise serializers.ValidationError({"type": TYPE_ERROR})
        if attrs["category"] != self.expected_category:
            raise serializers.ValidationError({"category": CATEGORY_ERROR})

        if attrs["type"] == ShipEquipment.TransactionType.EQUIPMENT:
            required = ("equipment_universal_id", "system_universal_id")
        else:
            required = ("system_universal_id",)
        for field in required:
            if not attrs.get(field):
                raise serializers.ValidationError({field: REQUIRED_SURVEY_DEMAND})
        return attrs

    class Meta(SFDTransactionBaseContractSerializer.Meta):
        fields = SFDTransactionBaseContractSerializer.Meta.fields + [
            "removal_date",
            "authority_of_removal",
            "new_installation_date",
            "new_serial_no",
            "installation_remark",
            "new_service_life",
        ]


class OthersSerializer(SFDTransactionBaseContractSerializer):
    """Local Purchase. The frontend's FIELD_SPECS deliberately reuses the Survey & Demand field
    set for this category (explicit product direction — see sfd-actions-fields.config.ts's
    OTHERS_FIELDS comment) and sfd-actions.service.ts's buildCreatePayload sends the identical
    SurveyDemandTransactionPayload shape for both, so this mirrors SurveySerializer exactly
    rather than the CAT3-style new_equipment_name/new_system_name shape the frontend never sends."""

    expected_category = ShipEquipment.TransactionCategory.OTHER
    removal_date = serializers.DateTimeField(
        help_text="Removal date and time for Local Purchase transactions."
    )
    authority_of_removal = serializers.CharField(
        help_text="Authority for removal on Local Purchase transactions."
    )
    new_installation_date = serializers.DateTimeField(
        help_text="New installation date and time for Local Purchase transactions."
    )
    new_serial_no = serializers.CharField(
        source="new_equipment_sr_no",
        help_text="New serial number for Local Purchase transactions.",
    )
    installation_remark = serializers.CharField(
        source="installation_remarks",
        help_text="Installation Remark for Local Purchase transactions.",
    )
    new_service_life = serializers.IntegerField(
        help_text="New Shelf Life for Local Purchase transactions."
    )

    def validate(self, attrs):
        required_fields = [
            "type",
            "category",
            "model_universal_id",
            "nomenclature",
            "supplier_universal_id",
            "manufacturer_universal_id",
            "oem_part_no",
            "equipment_serial_no",
            "location_on_board",
            "deck",
            "frame_station_from",
            "frame_station_to",
            "location_code",
            "installation_date",
            "authority_of_installation",
            "authority_date",
            "no_of_fits",
            "service_life",
            "equipment_section",
            "removal_date",
            "authority_of_removal",
            "new_equipment_sr_no",
            "new_installation_date",
            "new_service_life",
            "installation_remarks",
        ]
        for field in required_fields:
            if not attrs.get(field):
                raise serializers.ValidationError({field: REQUIRED_OTHERS})

        validations = {
            "qty_fitted": (attrs["no_of_fits"] > 0, QTY_FITTED_ERROR),
            "shell_life": (int(attrs["service_life"]) > 0, SHELL_LIFE_ERROR),
            "new_shell_life": (attrs["new_service_life"] > 0, SHELL_LIFE_ERROR),
            "installation_date": (
                _local_date(attrs["installation_date"]) <= timezone.localdate(),
                INVALID_FUTURE_DATE,
            ),
            "removal_date": (
                attrs["removal_date"] > attrs["installation_date"],
                "Removal Date Should be Ahead of Installation Date",
            ),
            "new_installation_date": (
                attrs["new_installation_date"] > attrs["removal_date"],
                "New Installation Date Should be Ahead of Removal Date",
            ),
        }
        for field, (is_valid, error) in validations.items():
            if not is_valid:
                raise serializers.ValidationError({field: error})

        if attrs["type"] not in {
            ShipEquipment.TransactionType.EQUIPMENT,
            ShipEquipment.TransactionType.SYSTEM,
        }:
            raise serializers.ValidationError({"type": TYPE_ERROR})
        if attrs["category"] != self.expected_category:
            raise serializers.ValidationError({"category": CATEGORY_ERROR})

        if attrs["type"] == ShipEquipment.TransactionType.EQUIPMENT:
            required = ("equipment_universal_id", "system_universal_id")
        else:
            required = ("system_universal_id",)
        for field in required:
            if not attrs.get(field):
                raise serializers.ValidationError({field: REQUIRED_OTHERS})
        return attrs

    class Meta(SFDTransactionBaseContractSerializer.Meta):
        fields = SFDTransactionBaseContractSerializer.Meta.fields + [
            "removal_date",
            "authority_of_removal",
            "new_installation_date",
            "new_serial_no",
            "installation_remark",
            "new_service_life",
        ]


DATE_FORMAT = "%d-%b-%Y"
DATETIME_FORMAT = "%d-%b-%Y %H:%M:%S"


def _format_dt(value, fmt):
    if not value:
        return None
    if isinstance(value, datetime):
        localized = timezone.localtime(value) if timezone.is_aware(value) else value
    else:
        localized = value
    return localized.strftime(fmt)


class SFDTransactionReportSerializer(serializers.Serializer):
    def to_representation(self, obj):
        dept_map = self.context.get("dept_map") or {}
        return {
            "equipment_name": _first_value(
                _equipment_display(getattr(obj, "equipment", None)),
                getattr(obj, "new_equipment_name", None),
            )
            or "",
            "sfd_category": getattr(obj, "category", None),
            "transaction_type": getattr(obj, "type", None),
            "transaction_date": _format_dt(
                getattr(obj, "created_at", None), DATETIME_FORMAT
            ),
            "status": _status_label(getattr(obj, "status", None)),
            "serial_no": _first_value(
                getattr(obj, "equipment_serial_no", None),
                getattr(obj, "new_equipment_sr_no", None),
            )
            or "",
            "department": _department_name(obj, dept_map),
        }


class EquipmentInstallationReportSerializer(serializers.Serializer):
    def to_representation(self, obj):
        supplier_map = self.context.get("supplier_map") or {}
        oem_val = supplier_map.get(getattr(obj, "universal_id_m_manufacturer", None))
        supplier_val = supplier_map.get(getattr(obj, "universal_id_m_supplier", None))
        return {
            "equipment_name": _first_value(
                _equipment_display(getattr(obj, "equipment", None)),
                getattr(obj, "new_equipment_name", None),
            )
            or "",
            "serial_no": _first_value(
                getattr(obj, "equipment_serial_no", None),
                getattr(obj, "new_equipment_sr_no", None),
            )
            or "",
            "oem": oem_val or getattr(obj, "new_manufacturer_name", None) or "",
            "supplier": supplier_val or getattr(obj, "new_supplier_name", None) or "",
            "installation_date": _format_dt(
                getattr(obj, "installation_date", None), DATE_FORMAT
            ),
            "installation_authority": _first_value(
                getattr(obj, "authority_of_installation", None),
                getattr(obj, "authority_installation", None),
            ),
            "deck_no": getattr(obj, "deck", None),
            "frame_station": getattr(obj, "frame", None) or "",
            "compartment": getattr(obj, "location_on_board", None),
        }


class EquipmentLocationReportSerializer(serializers.Serializer):
    def to_representation(self, obj):
        location_code = getattr(obj, "location_code", None)
        location_map = dict(ShipEquipment.Location.choices)
        return {
            "equipment_name": _first_value(
                _equipment_display(getattr(obj, "equipment", None)),
                getattr(obj, "new_equipment_name", None),
            )
            or "",
            "equipment_code": _first_value(
                getattr(getattr(obj, "equipment", None), "equipment_code", None),
                getattr(obj, "equipment_code", None),
            )
            or "",
            "deck_no": getattr(obj, "deck", None),
            "frame_station": getattr(obj, "frame", None) or "",
            "location": (
                f"{location_map.get(location_code, 'Unknown')} ({location_code})"
                if location_code
                else ""
            ),
            "compartment": getattr(obj, "location_on_board", None),
            "qty_fitted": getattr(obj, "no_of_fits", None),
        }


class RemovedEquipmentReportSerializer(serializers.Serializer):
    def to_representation(self, obj):
        tx = getattr(obj, "ship_equipment", None)
        equipment = getattr(obj, "equipment", None) or getattr(tx, "equipment", None)
        return {
            "equipment_code": getattr(equipment, "equipment_code", None) or "",
            "equipment_name": _first_value(
                _equipment_display(equipment),
                getattr(tx, "new_equipment_name", None),
            )
            or "",
            "serial_no": _first_value(
                getattr(obj, "equipment_serial_no", None),
                getattr(tx, "equipment_serial_no", None),
                getattr(tx, "new_equipment_sr_no", None),
            )
            or "",
            "removal_date": _format_dt(getattr(obj, "removal_date", None), DATE_FORMAT),
            "removal_remark": getattr(obj, "removal_remark", None),
            "removal_authority": getattr(obj, "authority_of_removal", None),
            "installation_authority": _first_value(
                getattr(obj, "authority_of_installation", None),
                getattr(tx, "authority_of_installation", None),
                getattr(tx, "authority_installation", None),
            ),
            "status": self._status(getattr(obj, "approved_reject", None)),
            "is_sync": self._is_sync(getattr(obj, "is_synced", None)),
        }

    @staticmethod
    def _status(value):
        status_map = {1: "approved", 2: "Pending", 3: "Rejected"}
        return status_map.get(value, str(value) if value is not None else "Pending")

    @staticmethod
    def _is_sync(value):
        if value == 1:
            return "sync"
        if value == 0 or value is None:
            return "not_sync"
        return str(value)


class ApprovalStatusReportSerializer(RemovedEquipmentReportSerializer):
    def to_representation(self, obj):
        data = super().to_representation(obj)
        request_type = getattr(obj, "request_type", None)
        data.update(
            {
                "rh_at_installation": getattr(
                    obj, "rh_of_new_equipment_at_time_of_installation", None
                ),
                "install_date": _format_dt(
                    getattr(obj, "installation_date", None), DATE_FORMAT
                ),
                "installation_remark": getattr(obj, "installation_remark", None),
                "approval_request_type": (
                    "Remove"
                    if request_type == 1
                    else "Change Sr. No."
                    if request_type == 2
                    else str(request_type)
                    if request_type is not None
                    else ""
                ),
            }
        )
        return data


class ShipEquipmentConfigurationReportSerializer(serializers.Serializer):
    def to_representation(self, obj):
        location_code = getattr(obj, "location_code", None)
        location_map = dict(ShipEquipment.Location.choices)
        dept_map = self.context.get("dept_map") or {}
        return {
            "equipment_name": _first_value(
                _equipment_display(getattr(obj, "equipment", None)),
                getattr(obj, "new_equipment_name", None),
            )
            or "",
            "transaction_type": getattr(obj, "type", None),
            "is_system": getattr(obj, "is_system", None),
            "transaction_category": getattr(obj, "category", None) or "",
            "equipment_sr_no": _first_value(
                getattr(obj, "equipment_serial_no", None),
                getattr(obj, "new_equipment_sr_no", None),
            )
            or "",
            "equipment_model": _first_value(
                getattr(obj, "equipment_model", None),
                getattr(getattr(obj, "equipment", None), "model", None),
            )
            or "",
            "equipment_nomenclature": _first_value(
                getattr(obj, "nomenclature", None),
                getattr(obj, "new_nomenclature", None),
            )
            or "",
            "location": (
                f"{location_map.get(location_code, 'Unknown')} ({location_code})"
                if location_code
                else ""
            ),
            "compartment": getattr(obj, "location_on_board", None),
            "oem_part_no": _first_value(
                getattr(obj, "oem_part_no", None),
                getattr(obj, "new_oem_part_no", None),
            )
            or "",
            "deck_no": getattr(obj, "deck", None),
            "installation_date": _format_dt(
                getattr(obj, "installation_date", None), DATE_FORMAT
            ),
            "manufacture": _first_value(
                _supplier_display(getattr(obj, "manufacturer", None)),
                getattr(obj, "new_manufacturer_name", None),
            )
            or "",
            "supplier": _first_value(
                _supplier_display(getattr(obj, "supplier", None)),
                getattr(obj, "new_supplier_name", None),
            )
            or "",
            "maintop_id": getattr(obj, "maintop_id", None),
            "service_life": getattr(obj, "service_life", None),
            "approval_status": _status_label(getattr(obj, "status", None)),
            "frame_station": getattr(obj, "frame", None),
            "department": _department_name(obj, dept_map),
            "sub_department": getattr(
                getattr(obj, "sub_department_f_key", None), "name", None
            )
            or "",
        }


class ReportExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportExportJob
        fields = "__all__"


class CompartmentViewSet(MessageModelViewSet):
    serializer_class = CompartmentSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CompartmentFilter
    search_fields = ["name"]
    ordering_fields = ["id", "name", "frame_station_from", "frame_station_to"]
    ordering = ["name"]
    create_message = "Compartment created successfully."
    update_message = "Compartment updated successfully."
    delete_message = "Compartment deleted successfully."

    def get_queryset(self):
        return CompartmentMaster.objects.filter(is_deleted=False)


class SubDepartmentViewSet(MessageModelViewSet):
    serializer_class = SubDepartmentContractSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = SubDepartmentFilter
    search_fields = ["name", "code"]
    ordering_fields = ["id", "name", "code"]
    ordering = ["code"]
    create_message = "Sub-department created successfully."
    update_message = "Sub-department updated successfully."
    delete_message = "Sub-department deleted successfully."

    def get_queryset(self):
        return SubDepartment.objects.select_related("department_name").filter(
            is_deleted=False
        )


class SFDTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = SourceShipEquipmentSerializer

    pagination_class = FrontendPageNumberPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["nomenclature", "equipment_serial_no", "oem_part_no"]
    ordering_fields = ["id", "nomenclature", "installation_date"]
    ordering = ["id"]

    serializer_map = {
        ShipEquipment.TransactionCategory.CAT1: CAT1Serializer,
        ShipEquipment.TransactionCategory.CAT2: CAT2Serializer,
        ShipEquipment.TransactionCategory.CAT3: CAT3Serializer,
        ShipEquipment.TransactionCategory.SURVEY: SurveySerializer,
        ShipEquipment.TransactionCategory.OTHER: OthersSerializer,
    }

    def get_serializer_class(self):
        # NOTE: cs_swmm_v1 checks `self.action in ("update")`, which — because
        # ("update") is a plain string, not a tuple — only matches when
        # self.action is itself the literal string "update" (PUT), never
        # "partial_update" (PATCH). Replicated here for byte-for-byte parity.
        if self.action in ("update"):
            instance = self.get_object()
            return self.serializer_map.get(
                instance.category, SourceShipEquipmentSerializer
            )
        return SourceShipEquipmentSerializer

    def get_queryset(self):
        queryset = (
            _ship_equipment_queryset()
            .select_related(
                "equipment",
                "system",
                "ship",
                "supplier",
                "manufacturer",
                "sub_department_f_key",
            )
            .all()
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(
                active=str(active).lower() in {"1", "true", "yes"}
            )
        equipment_name = self.request.query_params.get("equipment_name")
        if equipment_name:
            queryset = queryset.filter(
                Q(equipment__equipment_code=equipment_name)
                | Q(equipment__ilms_eq_code=equipment_name)
                | Q(equipment_name=equipment_name)
                | Q(new_equipment_name=equipment_name)
            )
        nomenclature = self.request.query_params.get("nomenclature")
        if nomenclature:
            queryset = queryset.filter(nomenclature=nomenclature)
        sub_dept = self.request.query_params.get("sub_dept")
        if sub_dept:
            if str(sub_dept).isdigit():
                queryset = queryset.filter(sub_department_f_key_id=int(sub_dept))
            else:
                queryset = queryset.filter(sub_department_f_key__name=sub_dept)
        maintop_id = self.request.query_params.get("maintop_id")
        if maintop_id:
            queryset = queryset.filter(maintop_id=maintop_id)
        return queryset

    @action(detail=True, methods=["get"], url_path="remove-details")
    def remove_details(self, request, pk=None):
        tx = self.get_object()
        return Response(
            {
                "equipment_nomenclature": tx.nomenclature,
                "equipment_sr_no": tx.equipment_serial_no,
                "sub_dept": (
                    tx.sub_department_f_key.name if tx.sub_department_f_key else ""
                ),
                "compartment_name": tx.location_on_board,
                "removal_date": None,
                "removal_authority": "",
                "removal_remark": "",
            }
        )

    @action(detail=True, methods=["post"], url_path="remove")
    def remove(self, request, pk=None):
        tx = self.get_object()
        removal_date = request.data.get("removal_date")
        removal_authority = request.data.get("removal_authority") or ""
        removal_remark = request.data.get("removal_remark") or ""
        remove_request = RemoveEquipment.objects.create(
            equipment=tx.equipment or Equipment.objects.first(),
            ship_equipment=tx,
            removal_remark=removal_remark,
            removal_date=removal_date,
            authority_of_removal=removal_authority,
            equipment_serial_no=tx.equipment_serial_no,
            request_type=1,
            is_synced=0,
        )
        return Response(
            RemoveEquipmentContractSerializer(remove_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="update_sr_no_details")
    def update_sr_no_details(self, request, pk=None):
        tx = self.get_object()
        return Response(
            {
                "equipment_nomenclature": tx.nomenclature,
                "current_sr_no": tx.equipment_serial_no,
                "sub_dept": (
                    tx.sub_department_f_key.name if tx.sub_department_f_key else ""
                ),
                "maintop_no": tx.maintop_id,
                "new_sr_no": "",
            }
        )

    @action(detail=True, methods=["post"], url_path="update_sr_no")
    def update_sr_no(self, request, pk=None):
        tx = self.get_object()
        new_sr_no = request.data.get("new_sr_no")
        remove_request = RemoveEquipment.objects.create(
            equipment=tx.equipment or Equipment.objects.first(),
            ship_equipment=tx,
            removal_remark="",
            equipment_serial_no=new_sr_no,
            request_type=2,
            is_synced=0,
        )
        return Response(
            RemoveEquipmentContractSerializer(remove_request).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="open-dependencies")
    def open_dependencies(self, request, pk=None):
        return Response({"open_defects": [], "maintenance_routines": []})


class ShipFitDefinitionViewSet(SFDTransactionViewSet):
    http_method_names = ["get", "patch", "head", "options"]


class SFDActionViewSet(viewsets.GenericViewSet):
    serializer_action_classes = {
        "cat1": CAT1Serializer,
        "cat2": CAT2Serializer,
        "cat3": CAT3Serializer,
        "survey_demand": SurveySerializer,
        "others": OthersSerializer,
    }

    def get_serializer_class(self):
        if self.action in self.serializer_action_classes:
            return self.serializer_action_classes[self.action]
        category_map = {
            "CAT1": CAT1Serializer,
            "CAT2": CAT2Serializer,
            "CAT3": CAT3Serializer,
            "SURVEY": SurveySerializer,
            "OTHER": OthersSerializer,
        }
        return category_map.get(
            self.request.data.get("transaction_category"), SourceShipEquipmentSerializer
        )

    def _create_transaction(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        response_serializer = self.get_serializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="cat1")
    def cat1(self, request):
        return self._create_transaction(request)

    @action(detail=False, methods=["post"], url_path="cat2")
    def cat2(self, request):
        return self._create_transaction(request)

    @action(detail=False, methods=["post"], url_path="cat3")
    def cat3(self, request):
        return self._create_transaction(request)

    @action(detail=False, methods=["post"], url_path="survey-demand")
    def survey_demand(self, request):
        return self._create_transaction(request)

    @action(detail=False, methods=["post"], url_path="others")
    def others(self, request):
        return self._create_transaction(request)


class EquipmentCompartmentMappingViewSet(MessageModelViewSet):
    serializer_class = EquipmentCompartmentMappingSerializer
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        return EquipmentCompartmentMapping.objects.select_related(
            "equipment", "compartment"
        )


def _resolve_universal_id(value):
    if isinstance(value, dict):
        return value.get("universal_id_t_equipment_ship_detail")
    return value


class EquipmentSystemMapSerializer(serializers.Serializer):
    equipment = serializers.JSONField(
        help_text=(
            "universal_id_t_equipment_ship_detail of the equipment row. Accepts "
            "either the raw id string or an object containing "
            "'universal_id_t_equipment_ship_detail'."
        )
    )
    system = serializers.JSONField(
        help_text=(
            "universal_id_t_equipment_ship_detail of the system row. Accepts "
            "either the raw id string or an object containing "
            "'universal_id_t_equipment_ship_detail'."
        )
    )

    def validate(self, attrs):
        equipment_id = _resolve_universal_id(attrs["equipment"])
        system_id = _resolve_universal_id(attrs["system"])

        if equipment_id == system_id:
            raise serializers.ValidationError(
                "Equipment and system must refer to different records."
            )

        equipment_row = ShipEquipment.objects.filter(
            universal_id_t_equipment_ship_detail=equipment_id
        ).first()
        if not equipment_row:
            raise serializers.ValidationError(
                {"equipment": "No matching equipment record found."}
            )

        system_row = ShipEquipment.objects.filter(
            universal_id_t_equipment_ship_detail=system_id
        ).first()
        if not system_row:
            raise serializers.ValidationError(
                {"system": "No matching system record found."}
            )

        attrs["equipment"] = equipment_id
        attrs["system"] = system_id
        attrs["equipment_row"] = equipment_row
        attrs["system_row"] = system_row
        return attrs

    def save(self, **kwargs):
        equipment_row = self.validated_data["equipment_row"]
        system_row = self.validated_data["system_row"]

        system_row.is_system = True
        system_row.save(update_fields=["is_system"])

        equipment_row.mapped_to = system_row.universal_id_t_equipment_ship_detail
        equipment_row.mapping_status = ShipEquipment.MappingStatus.MAPPED
        equipment_row.mapped_at = timezone.now()
        equipment_row.save(update_fields=["mapped_to", "mapping_status", "mapped_at"])

        return {"equipment_row": equipment_row, "system_row": system_row}


class EquipmentSystemMappingUpdateSerializer(serializers.Serializer):
    system = serializers.JSONField(required=False)
    mapping_status = serializers.ChoiceField(
        choices=ShipEquipment.MappingStatus.choices, required=False
    )

    def validate(self, attrs):
        if "system" not in attrs and "mapping_status" not in attrs:
            raise serializers.ValidationError(
                "At least one of 'system' or 'mapping_status' is required."
            )
        if "system" in attrs:
            system_id = _resolve_universal_id(attrs["system"])
            system_row = ShipEquipment.objects.filter(
                universal_id_t_equipment_ship_detail=system_id
            ).first()
            if not system_row:
                raise serializers.ValidationError(
                    {"system": "No matching system record found."}
                )
            attrs["system"] = system_id
            attrs["system_row"] = system_row
        return attrs


def _refresh_is_system(universal_id):
    has_mapping = ShipEquipment.objects.filter(
        mapped_to=universal_id, mapping_status=ShipEquipment.MappingStatus.MAPPED
    ).exists()
    ShipEquipment.objects.filter(
        universal_id_t_equipment_ship_detail=universal_id
    ).update(is_system=has_mapping)


class EquipmentSystemMappingFilter(django_filters.FilterSet):
    equipment = django_filters.CharFilter(
        field_name="universal_id_t_equipment_ship_detail"
    )
    system = django_filters.CharFilter(field_name="mapped_to")
    mapping_status = django_filters.CharFilter(field_name="mapping_status")
    addition_date_from = django_filters.DateFilter(
        field_name="mapped_at", lookup_expr="date__gte"
    )
    addition_date_to = django_filters.DateFilter(
        field_name="mapped_at", lookup_expr="date__lte"
    )

    class Meta:
        model = ShipEquipment
        fields = [
            "equipment",
            "system",
            "mapping_status",
            "addition_date_from",
            "addition_date_to",
        ]


class EquipmentSystemMappingViewSet(viewsets.GenericViewSet):
    http_method_names = ["get", "patch", "delete", "head", "options"]

    lookup_field = "universal_id_t_equipment_ship_detail"
    pagination_class = FrontendPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentSystemMappingFilter

    def get_queryset(self):
        return (
            ShipEquipment.objects.select_related("equipment")
            .exclude(mapped_to__isnull=True)
            .exclude(mapped_to="")
            .order_by("-mapped_at")
        )

    def _serialize(self, rows):
        rows = list(rows)
        system_rows = {
            row.universal_id_t_equipment_ship_detail: row
            for row in ShipEquipment.objects.select_related("equipment").filter(
                universal_id_t_equipment_ship_detail__in=[row.mapped_to for row in rows]
            )
        }
        data = []
        for row in rows:
            system_row = system_rows.get(row.mapped_to)
            data.append(
                {
                    "equipment": {
                        "universal_id_t_equipment_ship_detail": (
                            row.universal_id_t_equipment_ship_detail
                        ),
                        "label": equipment_label(
                            row.equipment.equipment_name if row.equipment else None,
                            row.location_on_board,
                        ),
                    },
                    "system": {
                        "universal_id_t_equipment_ship_detail": row.mapped_to,
                        "label": equipment_label(
                            system_row.equipment.equipment_name
                            if system_row and system_row.equipment
                            else None,
                            system_row.location_on_board if system_row else None,
                        ),
                    },
                    "addition_date": row.mapped_at,
                    "mapping_status": row.mapping_status,
                }
            )
        return data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        data = self._serialize(page if page is not None else queryset)
        if page is not None:
            return self.get_paginated_response(data)
        return Response({"message": "Mappings retrieved successfully.", "data": data})

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = EquipmentSystemMappingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        old_mapped_to = instance.mapped_to
        update_fields = []

        if "system_row" in validated:
            new_system_row = validated["system_row"]
            instance.mapped_to = new_system_row.universal_id_t_equipment_ship_detail
            update_fields.append("mapped_to")
            new_system_row.is_system = True
            new_system_row.save(update_fields=["is_system"])

        if "mapping_status" in validated:
            instance.mapping_status = validated["mapping_status"]
            update_fields.append("mapping_status")

        instance.save(update_fields=update_fields)

        if old_mapped_to and old_mapped_to != instance.mapped_to:
            _refresh_is_system(old_mapped_to)
        if instance.mapped_to:
            _refresh_is_system(instance.mapped_to)

        data = self._serialize([instance])[0]
        return Response({"message": "Mapping updated successfully.", "data": data})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        old_mapped_to = instance.mapped_to

        instance.mapped_to = None
        instance.mapping_status = None
        instance.mapped_at = None
        instance.save(update_fields=["mapped_to", "mapping_status", "mapped_at"])

        if old_mapped_to:
            _refresh_is_system(old_mapped_to)

        return Response({"message": "Mapping deleted successfully."})


class ConfigurationOptionsAPIView(APIView):
    def get(self, request):
        return Response(
            {
                "compartment": {
                    "upper_decks": [
                        {"value": value, "label": label}
                        for value, label in CompartmentMaster.UpperDeck.choices
                    ],
                    "lower_decks": [
                        {"value": value, "label": label}
                        for value, label in CompartmentMaster.LowerDeck.choices
                    ],
                    "locations": [
                        {"value": value, "label": label}
                        for value, label in CompartmentMaster.Location.choices
                    ],
                },
                "department": [
                    {"id": d.id, "value": d.id, "label": d.name, "code": d.code}
                    for d in Department.objects.order_by("name", "code")
                ],
            }
        )


class AddSFDEquipementAPIView(APIView):
    def get(self, request):
        ship_equipment_qs = _ship_equipment_queryset()
        transaction_universal_ids = ship_equipment_qs.values_list(
            "universal_id_m_equipment", flat=True
        ).distinct()

        equipment_details = (
            Equipment.objects.filter(
                universal_id_m_equipment__in=transaction_universal_ids
            )
            .exclude(
                Q(equipment_class__isnull=True)
                & Q(equipment_code__isnull=True)
                & Q(ilms_eq_code__isnull=True)
            )
            .exclude(Q(equipment_class="") & Q(equipment_code="") & Q(ilms_eq_code=""))
            .values(
                "universal_id_m_equipment",
                "equipment_class",
                "equipment_code",
                "ilms_eq_code",
            )
            .distinct()
        )
        equipment_names = [
            {
                "universal_id_m_equipment": item["universal_id_m_equipment"],
                "equipment_name": (
                    item["equipment_class"]
                    or item["equipment_code"]
                    or item["ilms_eq_code"]
                ),
            }
            for item in equipment_details
        ]
        system_names = [
            {
                "universal_id_m_equipment": item["universal_id_m_equipment"],
                "system_name": (
                    item["equipment_class"]
                    or item["equipment_code"]
                    or item["ilms_eq_code"]
                ),
            }
            for item in equipment_details
        ]

        model_details = (
            Equipment.objects.filter(
                universal_id_m_equipment__in=transaction_universal_ids
            )
            .exclude(model__isnull=True)
            .exclude(model="")
            .values("universal_id_m_equipment", "model")
            .distinct()
        )
        models_list = [
            {
                "universal_id_m_equipment": item["universal_id_m_equipment"],
                "model": item["model"],
            }
            for item in model_details
        ]

        nomenclature_details = (
            ship_equipment_qs.exclude(
                Q(nomenclature__isnull=True) & Q(new_nomenclature__isnull=True)
            )
            .exclude(Q(nomenclature="") & Q(new_nomenclature=""))
            .values("universal_id_m_equipment", "nomenclature", "new_nomenclature")
            .distinct()
        )
        nomenclatures = [
            {
                "universal_id_m_equipment": item["universal_id_m_equipment"],
                "Nomenclature": item["nomenclature"] or item["new_nomenclature"],
            }
            for item in nomenclature_details
        ]

        equipment_sr_no_details = (
            ship_equipment_qs.exclude(
                Q(equipment_serial_no__isnull=True)
                & Q(new_equipment_sr_no__isnull=True)
            )
            .exclude(Q(equipment_serial_no="") & Q(new_equipment_sr_no=""))
            .values(
                "universal_id_m_equipment", "equipment_serial_no", "new_equipment_sr_no"
            )
            .distinct()
        )
        equipment_sr_no = [
            {
                "universal_id_m_equipment": item["universal_id_m_equipment"],
                "Equipment_sr_no": item["equipment_serial_no"]
                or item["new_equipment_sr_no"],
            }
            for item in equipment_sr_no_details
        ]

        manufacturer_universal_ids = list(
            ship_equipment_qs.exclude(universal_id_m_manufacturer__isnull=True)
            .exclude(universal_id_m_manufacturer="")
            .values_list("universal_id_m_manufacturer", flat=True)
            .distinct()
        )
        manufacturer_details = (
            Supplier.objects.filter(
                Universal_ID_M_Supplier__in=manufacturer_universal_ids
            )
            .exclude(SupplierName__isnull=True, supplier_name__isnull=True)
            .values(
                "Universal_ID_M_Supplier",
                "SupplierName",
                "supplier_name",
            )
            .distinct()
        )
        manufacturers = [
            {
                "universal_id_M_supplier": item["Universal_ID_M_Supplier"],
                "manufacturer_name": item["SupplierName"] or item["supplier_name"],
            }
            for item in manufacturer_details
            if item["SupplierName"] or item["supplier_name"]
        ]

        supplier_universal_ids = list(
            ship_equipment_qs.exclude(universal_id_m_supplier__isnull=True)
            .exclude(universal_id_m_supplier="")
            .values_list("universal_id_m_supplier", flat=True)
            .distinct()
        )
        supplier_details = (
            Supplier.objects.filter(Universal_ID_M_Supplier__in=supplier_universal_ids)
            .values("Universal_ID_M_Supplier", "SupplierName", "supplier_name")
            .distinct()
        )
        suppliers = [
            {
                "universal_id_M_supplier": item["Universal_ID_M_Supplier"],
                "supplier_name": item["SupplierName"] or item["supplier_name"],
            }
            for item in supplier_details
            if item["SupplierName"] or item["supplier_name"]
        ]

        oem_parts_details = (
            ship_equipment_qs.exclude(
                Q(oem_part_no__isnull=True) & Q(new_oem_part_no__isnull=True)
            )
            .exclude(Q(oem_part_no="") & Q(new_oem_part_no=""))
            .values("universal_id_m_equipment", "oem_part_no", "new_oem_part_no")
            .distinct()
        )
        oem_parts = [
            {
                "universal_id_m_equipment": item["universal_id_m_equipment"],
                "oem_part_no": item["oem_part_no"] or item["new_oem_part_no"],
            }
            for item in oem_parts_details
        ]

        compartment_details = (
            CompartmentMaster.objects.exclude(name__isnull=True)
            .exclude(name="")
            .values("id", "name")
            .distinct()
        )
        compartment_names = [
            {"compartment_id": item["id"], "compartment_name": item["name"]}
            for item in compartment_details
        ]

        shelf_lifes_details = (
            ship_equipment_qs.exclude(service_life__isnull=True)
            .exclude(service_life="")
            .values_list("service_life", flat=True)
            .distinct()
        )
        shelf_lifes = [
            {"shelf_lifes_id": item, "shelf_lifes_name": item}
            for item in shelf_lifes_details
        ]

        sub_dept_universal_ids = list(
            ship_equipment_qs.exclude(universal_id_m_sub_department__isnull=True)
            .exclude(universal_id_m_sub_department="")
            .values_list("universal_id_m_sub_department", flat=True)
            .distinct()
        )
        section_details = (
            SubDepartment.objects.filter(
                universal_id_m_sub_department__in=sub_dept_universal_ids
            )
            .exclude(name__isnull=True)
            .exclude(name="")
            .values("universal_id_m_sub_department", "name")
            .distinct()
        )
        equipment_sections = [
            {
                "universal_id_m_sub_department": item["universal_id_m_sub_department"],
                "sub_department_name": item["name"],
            }
            for item in section_details
        ]

        ch_eq_type_universal_ids = list(
            ship_equipment_qs.exclude(
                universal_id_ch_master_equipment_type__isnull=True
            )
            .exclude(universal_id_ch_master_equipment_type="")
            .values_list("universal_id_ch_master_equipment_type", flat=True)
            .distinct()
        )
        ch_eq_type_details = (
            EquipmentType.objects.filter(
                universal_id_ch_master_equipment_type__in=ch_eq_type_universal_ids
            )
            .exclude(equipment_desc__isnull=True)
            .exclude(equipment_desc="")
            .values("universal_id_ch_master_equipment_type", "equipment_desc")
            .distinct()
        )
        equipment_types = [
            {
                "universal_id_ch_master_equipment_type": item[
                    "universal_id_ch_master_equipment_type"
                ],
                "name": item["equipment_desc"],
            }
            for item in ch_eq_type_details
        ]

        return Response(
            {
                "equipment_name": equipment_names,
                "system_name": system_names,
                "model": models_list,
                "Nomenclature": nomenclatures,
                "Equipment Sr No": equipment_sr_no,
                "OEM Name": manufacturers,
                "Supplier": suppliers,
                "OEM Part No": oem_parts,
                "Compartment Name": compartment_names,
                "Shelf Life": shelf_lifes,
                "Equipment Section": equipment_sections,
                "Equipment Type": equipment_types,
            }
        )


class ReferenceStandardDepartmentListAPIView(generics.ListAPIView):
    pagination_class = FrontendPageNumberPagination

    def list(self, request, *args, **kwargs):
        department_ids = _ship_equipment_queryset().values_list(
            "department_id", flat=True
        )
        rows = list(Department.objects.filter(id__in=department_ids).order_by("name"))
        dept_ids = [row.id for row in rows]

        sub_depts_map = {}
        for sd in SubDepartment.objects.filter(department_name_id__in=dept_ids).values(
            "department_name_id", "name"
        ):
            if sd["name"]:
                sub_depts_map.setdefault(sd["department_name_id"], []).append(
                    sd["name"]
                )

        hods_map = {
            hod.department_id: hod
            for hod in CustomUserProfile.objects.filter(
                department_id__in=dept_ids, designation__iexact="HOD"
            ).only("id", "department_id", "firstname", "lastname", "personal_number")
        }

        data = []
        for row in rows:
            hod = hods_map.get(row.id)
            if hod:
                full_name = f"{hod.firstname or ''} {hod.lastname or ''}".strip()
                hod_name = full_name or ""
                personal_no = hod.personal_number or ""
            else:
                hod_name = ""
                personal_no = ""
            data.append(
                {
                    "dept_id": row.id,
                    "dept_code": row.code,
                    "dept_name": row.name,
                    "no_of_sub_department": len(sub_depts_map.get(row.id, [])),
                    "hod": hod_name,
                    "personal_no": personal_no,
                }
            )
        return _paginated_response(request, data)


class ReferenceShipDetailsAPIView(APIView):
    def get(self, request):
        ship = _active_ship()
        if not ship:
            return Response(
                {"detail": "No ship details found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "ship_id": ship.id,
                "ship_sr_no": ship.sr_no,
                "ship_name": ship.name,
                "class_code": _first_value(
                    getattr(ship.class_master, "description", None),
                    ship.class_code,
                ),
                "commission_date": (
                    ship.commission_date.strftime("%d-%b-%Y")
                    if getattr(ship, "commission_date", None)
                    else ""
                ),
                "ops_code": _first_value(
                    ship.ops_code,
                    getattr(ship.authority, "ops_authority", None),
                ),
                "ship_builder": ship.ship_builder,
                "displacement": ship.displacement,
                "yard_no": ship.yard_no,
                "length_overall": ship.length_overall,
                "refit_authority": ship.refit_authority,
                "address": ship.address,
                "ship_category": getattr(
                    ship.ship_category, "ship_category_name", None
                ),
                "propulsion": getattr(ship.propulsion, "propulsion_name", None),
            }
        )


class ReferenceEquipmentMasterListAPIView(generics.ListAPIView):
    serializer_class = serializers.Serializer

    pagination_class = FrontendPageNumberPagination

    def list(self, request, *args, **kwargs):
        universal_ids = _ship_equipment_queryset().values_list(
            "universal_id_m_equipment", flat=True
        )
        equipment_rows = Equipment.objects.filter(
            universal_id_m_equipment__in=universal_ids
        ).order_by("id")
        data = [
            {
                "equipment_id": e.id,
                "equipment_code": e.equipment_code,
                "equipment_name": _equipment_display(e),
                "equipment_model": _first_value(
                    getattr(e, "equipment_model", None),
                    getattr(e, "model", None),
                ),
                "maintop_number": getattr(e, "maintop_number", None),
                "manufacturer_name": getattr(e, "manufacturer_name", None),
                "authority": getattr(e, "authority", None),
                "ilms_equipment_code": _first_value(
                    getattr(e, "ilms_equipment_code", None),
                    getattr(e, "ilms_eq_code", None),
                ),
                "universal_id_m_equipment": getattr(
                    e, "universal_id_m_equipment", None
                ),
            }
            for e in equipment_rows
        ]
        return _paginated_response(request, data)


class ReferenceSystemMasterListAPIView(ReferenceEquipmentMasterListAPIView):
    def list(self, request, *args, **kwargs):
        universal_ids = _ship_equipment_queryset().values_list(
            "universal_id_m_equipment", flat=True
        )
        equipment_rows = Equipment.objects.filter(
            universal_id_m_equipment__in=universal_ids
        ).order_by("id")
        data = [
            {
                "system_id": e.id,
                "system_code": e.equipment_code,
                "system_name": _equipment_display(e),
                "system_model": _first_value(
                    getattr(e, "equipment_model", None),
                    getattr(e, "model", None),
                ),
                "maintop_number": getattr(e, "maintop_number", None),
                "manufacturer_name": getattr(e, "manufacturer_name", None),
                "authority": getattr(e, "authority", None),
                "ilms_system_code": _first_value(
                    getattr(e, "ilms_equipment_code", None),
                    getattr(e, "ilms_eq_code", None),
                ),
                "universal_id_m_system": getattr(e, "universal_id_m_equipment", None),
            }
            for e in equipment_rows
        ]
        return _paginated_response(request, data)


class EquipmentDropdownAPIView(APIView):
    """`get_equipment/` — single-record lookup by universal_id_m_equipment,
    matching cs_swmm_v1's contract (NOT a bulk dropdown list). An equipment can have several
    distinct nomenclatures across its fitted history (different installs, different names) — an
    optional `nomenclature` param narrows the match to the specific record the user actually
    picked, so OEM/Supplier/Shelf Life/Deck/Location/Compartment reflect that record rather than
    an arbitrary one sharing the same equipment. When `nomenclature` is given and nothing matches
    it, this 404s rather than silently falling back to a DIFFERENT nomenclature's data — showing
    the wrong equipment's OEM/Supplier/Shelf Life as if it were correct is worse than the frontend
    just leaving those fields blank for manual entry. The equipment-only lookup (no `nomenclature`
    param at all) still returns *some* match if one exists, since that path is only used to check
    whether the equipment itself is already mapped to a system."""

    def get(self, request):
        universal_id = request.query_params.get("universal_id_m_equipment")
        if not universal_id:
            return Response(
                {"detail": "universal_id_m_equipment is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_qs = ShipEquipment.objects.select_related(
            "equipment", "manufacturer", "supplier"
        ).filter(universal_id_m_equipment=universal_id)

        nomenclature = request.query_params.get("nomenclature")
        if nomenclature:
            tx = base_qs.filter(
                Q(nomenclature=nomenclature) | Q(new_nomenclature=nomenclature)
            ).first()
        else:
            tx = base_qs.first()
        if tx is None:
            return Response(
                {"detail": "Equipment not found."}, status=status.HTTP_404_NOT_FOUND
            )

        equipment = tx.equipment
        equipment_uid = (
            getattr(equipment, "universal_id_m_equipment", None) if equipment else None
        )
        section_uid = tx.universal_id_m_sub_department or (
            tx.sub_department_f_key.universal_id_m_sub_department
            if tx.sub_department_f_key
            else None
        )

        mapped_system_uid = None
        if tx.mapping_status == ShipEquipment.MappingStatus.MAPPED and tx.mapped_to:
            system_row = (
                ShipEquipment.objects.select_related("equipment")
                .filter(universal_id_t_equipment_ship_detail=tx.mapped_to)
                .first()
            )
            if system_row:
                mapped_system_uid = system_row.universal_id_m_equipment or getattr(
                    system_row.equipment, "universal_id_m_equipment", None
                )

        return Response(
            {
                "system_id": equipment_uid,
                "model_id": equipment_uid,
                "nomenclature_id": equipment_uid,
                "oem_name_id": tx.universal_id_m_manufacturer or None,
                "supplier_id": tx.universal_id_m_supplier or None,
                "oem_part_no_id": equipment_uid,
                "equipment_sr_no": tx.equipment_serial_no or tx.new_equipment_sr_no,
                "shelf_life_id": tx.service_life,
                "deck_no": tx.deck,
                "frame_station": tx.frame,
                "location": tx.location_code,
                "location_name": dict(ShipEquipment.Location.choices).get(
                    tx.location_code
                ),
                "compartrment": tx.location_on_board,
                "installation_date": tx.installation_date or tx.new_installation_date,
                "installation_remarks": tx.installation_remarks,
                "qty_fitted": tx.no_of_fits,
                "sub_department": section_uid,
                "new_shelf_life": tx.new_service_life,
                "is_mapped": mapped_system_uid is not None,
                "mapped_system_id": mapped_system_uid,
            }
        )


class _MasterEquipmentDropdownAPIView(APIView):
    """Flat master-equipment dropdown list. Used by the compartment dropdown
    helper (A-only) — no longer shared with `get_equipment/`."""

    def get(self, request):
        return Response(
            [
                {
                    "id": e.id,
                    "value": e.universal_id_m_equipment or str(e.id),
                    "label": _equipment_display(e),
                    "equipment_code": e.equipment_code,
                }
                for e in Equipment.objects.order_by("equipment_code")
            ]
        )


class EquipmentSystemDropdownAPIView(APIView):
    def get(self, request):
        rows = (
            ShipEquipment.objects.select_related("equipment")
            .exclude(equipment__isnull=True)
            .exclude(equipment_name__isnull=True)
            .exclude(equipment_name="")
            .values(
                "universal_id_t_equipment_ship_detail",
                "equipment_name",
                "location_on_board",
            )
            .distinct()
        )
        options = [
            {
                "universal_id_t_equipment_ship_detail": row[
                    "universal_id_t_equipment_ship_detail"
                ],
                "label": equipment_label(
                    row["equipment_name"], row["location_on_board"]
                ),
            }
            for row in rows
        ]
        return Response({"equipment": options, "system": options})


class EquipmentCompartmentDropdownAPIView(APIView):
    def get(self, request):
        return Response(
            {
                "equipment": _MasterEquipmentDropdownAPIView().get(request).data,
                "compartment": [
                    {
                        "id": c.id,
                        "label": c.name,
                        "value": c.id,
                        "main_deck": c.main_deck,
                        "upper_deck": c.upper_deck,
                        "lower_deck": c.lower_deck,
                        "frame_station_from": c.frame_station_from,
                        "frame_station_to": c.frame_station_to,
                        "location": c.location,
                    }
                    for c in CompartmentMaster.objects.filter(is_deleted=False)
                ],
            }
        )


class EquipmentCompartmentMapAPIView(APIView):
    def post(self, request):
        serializer = EquipmentCompartmentMappingSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        mapping = serializer.save()
        return Response(
            EquipmentCompartmentMappingSerializer(mapping).data,
            status=status.HTTP_201_CREATED,
        )


class EquipmentSystemMapAPIView(APIView):
    def post(self, request):
        serializer = EquipmentSystemMapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {
                "message": "Equipment mapped to system successfully.",
                "data": {
                    "equipment": (
                        result["equipment_row"].universal_id_t_equipment_ship_detail
                    ),
                    "system": (
                        result["system_row"].universal_id_t_equipment_ship_detail
                    ),
                },
            }
        )


class EquipmentSystemMappingAPIView(EquipmentSystemMapAPIView):
    pass


class EquipmentSystemUpdateAPIView(APIView):
    def patch(self, request, equipment_id):
        viewset = EquipmentSystemMappingViewSet()
        viewset.request = request
        viewset.kwargs = {viewset.lookup_field: equipment_id}
        return viewset.partial_update(request)


class EquipmentSystemUnmapAPIView(APIView):
    def delete(self, request, equipment_id):
        viewset = EquipmentSystemMappingViewSet()
        viewset.request = request
        viewset.kwargs = {viewset.lookup_field: equipment_id}
        return viewset.destroy(request)


class _ShipEquipmentListAPIView(generics.ListAPIView):
    serializer_class = SourceShipEquipmentSerializer

    pagination_class = FrontendPageNumberPagination

    def get_queryset(self):
        return ShipEquipment.objects.select_related(
            "equipment",
            "supplier",
            "manufacturer",
            "ship",
            "sub_department_f_key",
            "sub_department_f_key__department_name",
        ).all()


class SFDTransactionReportFilter(django_filters.FilterSet):
    sfd_category = django_filters.CharFilter(field_name="category")
    transaction_type = django_filters.CharFilter(field_name="type")
    equipment_name = django_filters.CharFilter(method="filter_equipment_name")
    department = django_filters.NumberFilter(method="filter_department")
    date_filter = django_filters.CharFilter(method="filter_date")

    class Meta:
        model = ShipEquipment
        fields = ["sfd_category", "transaction_type", "equipment_name", "department"]

    def filter_equipment_name(self, queryset, name, value):
        return queryset.filter(
            Q(equipment__equipment_code=value)
            | Q(equipment__ilms_eq_code=value)
            | Q(new_equipment_name=value)
        )

    def filter_department(self, queryset, name, value):
        return _filter_by_department(queryset, {"department": value})

    def filter_date(self, queryset, name, value):
        return queryset.filter(_resolve_date_filter(value, "created_at"))


class SFDTransactionReportAPIView(_ShipEquipmentListAPIView):
    serializer_class = SFDTransactionReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SFDTransactionReportFilter

    def get_queryset(self):
        # ShipEquipment doubles as both "equipment fitted on this ship" (every CMMS-synced row)
        # and "SFD transaction record" (SFDTransaction = ShipEquipment, sfd/models.py) — but only
        # a row an actual CAT I/II/III/Survey/Local-Purchase Action was submitted for ever gets
        # `type` set (Step 1's CMMS sync never touches it). Without this filter every baseline
        # equipment record shows up here too, even ones no SFD transaction has ever happened for.
        return (
            super()
            .get_queryset()
            .exclude(type__isnull=True)
            .exclude(type="")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dept_map"] = {
            d.universal_id_m_department: (d.name or d.code or "")
            for d in Department.objects.all()
            if d.universal_id_m_department
        }
        return context


class EquipmentInstallationReportFilter(django_filters.FilterSet):
    date_filter = django_filters.CharFilter(method="filter_date")
    supplier = django_filters.CharFilter(field_name="universal_id_m_supplier")
    oem = django_filters.CharFilter(field_name="universal_id_m_manufacturer")

    class Meta:
        model = ShipEquipment
        fields = ["date_filter", "supplier", "oem"]

    def filter_date(self, queryset, name, value):
        return queryset.filter(_resolve_date_filter(value, "installation_date"))


class EquipmentInstallationReportAPIView(_ShipEquipmentListAPIView):
    serializer_class = EquipmentInstallationReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentInstallationReportFilter

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(installation_date__isnull=False)
            .order_by("-installation_date")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["supplier_map"] = {
            s["Universal_ID_M_Supplier"]: s["SupplierName"] or s["supplier_name"] or ""
            for s in Supplier.objects.values(
                "Universal_ID_M_Supplier", "SupplierName", "supplier_name"
            )
            if s["Universal_ID_M_Supplier"]
        }
        return context


class EquipmentLocationReportFilter(django_filters.FilterSet):
    location = django_filters.CharFilter(field_name="location_code")
    qty_fitted = django_filters.NumberFilter(field_name="no_of_fits")
    compartment = django_filters.CharFilter(
        field_name="location_on_board", lookup_expr="icontains"
    )

    class Meta:
        model = ShipEquipment
        fields = ["location", "qty_fitted", "compartment"]


class EquipmentLocationReportAPIView(_ShipEquipmentListAPIView):
    serializer_class = EquipmentLocationReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentLocationReportFilter

    def get_queryset(self):
        return super().get_queryset().order_by("-created_at")


class ShipEquipmentConfigurationReportFilter(django_filters.FilterSet):
    transaction_type = django_filters.CharFilter(field_name="type")
    transaction_category = django_filters.CharFilter(field_name="category")
    sub_department = django_filters.NumberFilter(field_name="sub_department_f_key_id")
    system = django_filters.CharFilter(field_name="mapped_to")
    location = django_filters.CharFilter(field_name="location_code")
    compartment = django_filters.CharFilter(
        field_name="location_on_board", lookup_expr="icontains"
    )
    installation_date = django_filters.CharFilter(method="filter_installation_date")
    removal_date = django_filters.CharFilter(method="filter_removal_date")
    manufacture = django_filters.CharFilter(field_name="universal_id_m_manufacturer")
    supplier = django_filters.CharFilter(field_name="universal_id_m_supplier")
    service_life = django_filters.CharFilter(field_name="service_life")
    approval_status = django_filters.CharFilter(field_name="status")
    department = django_filters.NumberFilter(method="filter_department")

    class Meta:
        model = ShipEquipment
        fields = [
            "transaction_type",
            "transaction_category",
            "sub_department",
            "system",
            "location",
            "compartment",
            "installation_date",
            "removal_date",
            "manufacture",
            "supplier",
            "service_life",
            "approval_status",
            "department",
        ]

    def filter_removal_date(self, queryset, name, value):
        return queryset.filter(_resolve_date_filter(value, "removal_date"))

    def filter_installation_date(self, queryset, name, value):
        q_inst = _resolve_date_filter(value, "installation_date")
        q_new = _resolve_date_filter(value, "new_installation_date")
        return queryset.filter(q_inst | q_new)

    def filter_department(self, queryset, name, value):
        return _filter_by_department(queryset, {"department": value})


class ShipEquipmentConfigurationReportAPIView(_ShipEquipmentListAPIView):
    serializer_class = ShipEquipmentConfigurationReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ShipEquipmentConfigurationReportFilter

    def get_queryset(self):
        return super().get_queryset().order_by("-created_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["dept_map"] = {
            d.universal_id_m_department: (d.name or d.code or "")
            for d in Department.objects.all()
            if d.universal_id_m_department
        }
        return context


class RemovedEquipmentReportFilter(django_filters.FilterSet):
    removal_date = django_filters.CharFilter(method="filter_removal_date")
    status = django_filters.NumberFilter(field_name="approved_reject")
    removed_authority = django_filters.CharFilter(
        field_name="authority_of_removal", lookup_expr="icontains"
    )

    class Meta:
        model = RemoveEquipment
        fields = ["removal_date", "status", "removed_authority"]

    def filter_removal_date(self, queryset, name, value):
        return queryset.filter(_resolve_date_filter(value, "removal_date"))


class RemovedEquipmentReportAPIView(generics.ListAPIView):
    serializer_class = RemovedEquipmentReportSerializer

    pagination_class = FrontendPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RemovedEquipmentReportFilter
    queryset = (
        RemoveEquipment.objects.select_related("equipment", "ship_equipment")
        .filter(request_type=1)
        .order_by("-removal_date", "-id")
    )


class ApprovalStatusReportFilter(django_filters.FilterSet):
    removal_date = django_filters.CharFilter(method="filter_removal_date")
    install_date = django_filters.CharFilter(method="filter_install_date")
    status = django_filters.NumberFilter(field_name="approved_reject")
    removed_authority = django_filters.CharFilter(
        field_name="authority_of_removal", lookup_expr="icontains"
    )
    approval_request_type = django_filters.NumberFilter(field_name="request_type")

    class Meta:
        model = RemoveEquipment
        fields = [
            "removal_date",
            "install_date",
            "status",
            "removed_authority",
            "approval_request_type",
        ]

    def filter_removal_date(self, queryset, name, value):
        return queryset.filter(_resolve_date_filter(value, "removal_date"))

    def filter_install_date(self, queryset, name, value):
        return queryset.filter(_resolve_date_filter(value, "installation_date"))


class ApprovalStatusReportAPIView(RemovedEquipmentReportAPIView):
    serializer_class = ApprovalStatusReportSerializer
    filterset_class = ApprovalStatusReportFilter
    queryset = (
        RemoveEquipment.objects.select_related("equipment", "ship_equipment")
        .all()
        .order_by("-removal_date", "-id")
    )


def _get_equipment_names():
    rows = _ship_equipment_queryset().select_related("equipment")
    names = set()
    for row in rows:
        name = (
            row.equipment_name
            or row.new_equipment_name
            or getattr(row.equipment, "equipment_class", None)
            or row.nomenclature
        )
        if name:
            names.add(name)
    return [{"value": name, "label": name} for name in sorted(names)]


def _get_sfd_list_nomenclatures():
    values = list(
        _ship_equipment_queryset()
        .exclude(nomenclature__isnull=True)
        .exclude(nomenclature="")
        .values_list("nomenclature", flat=True)
        .distinct()
        .order_by("nomenclature")
    )
    return [{"value": value, "label": value} for value in values]


def _get_sfd_list_sub_departments():
    rows = (
        _ship_equipment_queryset()
        .filter(sub_department_f_key__isnull=False)
        .values("sub_department_f_key_id", "sub_department_f_key__name")
        .distinct()
        .order_by("sub_department_f_key__name")
    )
    return [
        {
            "value": row["sub_department_f_key_id"],
            "label": row["sub_department_f_key__name"],
        }
        for row in rows
        if row["sub_department_f_key_id"] and row["sub_department_f_key__name"]
    ]


def _get_sfd_list_maintops():
    values = list(
        _ship_equipment_queryset()
        .exclude(maintop_id__isnull=True)
        .values_list("maintop_id", flat=True)
        .distinct()
        .order_by("maintop_id")
    )
    return [{"value": value, "label": str(value)} for value in values]


def _get_system_options():
    system_ids = list(
        _ship_equipment_queryset()
        .exclude(mapped_to__isnull=True)
        .exclude(mapped_to="")
        .values_list("mapped_to", flat=True)
        .distinct()
    )
    rows = (
        _ship_equipment_queryset()
        .select_related("equipment")
        .filter(universal_id_t_equipment_ship_detail__in=system_ids)
    )
    return [
        {
            "value": row.universal_id_t_equipment_ship_detail,
            "label": equipment_label(
                row.equipment.equipment_name if row.equipment else row.equipment_name,
                row.location_on_board,
            ),
        }
        for row in rows
        if row.universal_id_t_equipment_ship_detail
    ]


def _get_sfd_categories():
    return [
        {"value": value, "label": label}
        for value, label in ShipEquipment.TransactionCategory.choices
    ]


def _get_transaction_types():
    return [
        {"value": value, "label": label}
        for value, label in ShipEquipment.TransactionType.choices
    ]


def _get_departments():
    return [
        {
            "value": d["id"],
            "label": (
                f"{d['name']} ({d['code']})"
                if d["name"] and d["code"]
                else (d["name"] or d["code"] or "")
            ),
        }
        for d in Department.objects.values("id", "name", "code").order_by("id")
    ]


def _get_suppliers():
    used_ids = list(
        ShipEquipment.objects.exclude(universal_id_m_supplier__isnull=True)
        .exclude(universal_id_m_supplier="")
        .values_list("universal_id_m_supplier", flat=True)
        .distinct()
    )
    return [
        {
            "value": s["Universal_ID_M_Supplier"],
            "label": s["SupplierName"] or s["supplier_name"] or "",
        }
        for s in Supplier.objects.filter(
            Q(supplier_manufacture=1) | Q(SupplierManufacturer="1"),
            Universal_ID_M_Supplier__in=used_ids,
        )
        .values("Universal_ID_M_Supplier", "SupplierName", "supplier_name")
        .order_by("SupplierName")
        if (s["SupplierName"] or s["supplier_name"]) and s["Universal_ID_M_Supplier"]
    ]


def _get_oems():
    used_ids = list(
        ShipEquipment.objects.exclude(universal_id_m_manufacturer__isnull=True)
        .exclude(universal_id_m_manufacturer="")
        .values_list("universal_id_m_manufacturer", flat=True)
        .distinct()
    )
    return [
        {
            "value": s["Universal_ID_M_Supplier"],
            "label": s["SupplierName"] or s["supplier_name"] or "",
        }
        for s in Supplier.objects.filter(
            Q(supplier_manufacture=2) | Q(SupplierManufacturer="2"),
            Universal_ID_M_Supplier__in=used_ids,
        )
        .values("Universal_ID_M_Supplier", "SupplierName", "supplier_name")
        .order_by("SupplierName")
        if (s["SupplierName"] or s["supplier_name"]) and s["Universal_ID_M_Supplier"]
    ]


def _get_compartment_options():
    values = list(
        ShipEquipment.objects.exclude(location_on_board__isnull=True)
        .exclude(location_on_board="")
        .values_list("location_on_board", flat=True)
        .distinct()
        .order_by("location_on_board")
    )
    return [{"value": val, "label": val} for val in values]


def _get_qty_fitted_options():
    values = list(
        ShipEquipment.objects.exclude(no_of_fits__isnull=True)
        .values_list("no_of_fits", flat=True)
        .distinct()
        .order_by("no_of_fits")
    )
    return [{"value": val, "label": str(val)} for val in values]


def _get_location_code_options():
    codes = list(
        ShipEquipment.objects.exclude(location_code__isnull=True)
        .exclude(location_code="")
        .values_list("location_code", flat=True)
        .distinct()
        .order_by("location_code")
    )
    choices_dict = dict(ShipEquipment.Location.choices)
    return [
        {"value": code, "label": f"{choices_dict.get(code, 'Unknown')} ({code})"}
        for code in codes
    ]


def _get_remove_authority_options():
    values = list(
        RemoveEquipment.objects.exclude(authority_of_removal__isnull=True)
        .exclude(authority_of_removal="")
        .values_list("authority_of_removal", flat=True)
        .distinct()
        .order_by("authority_of_removal")
    )
    return [{"value": val, "label": val} for val in values]


def _get_remove_status_options():
    values = list(
        RemoveEquipment.objects.exclude(approved_reject__isnull=True)
        .values_list("approved_reject", flat=True)
        .distinct()
        .order_by("approved_reject")
    )
    status_map = {1: "approved", 2: "Pending", 3: "Rejected"}
    return [{"value": val, "label": status_map.get(val, str(val))} for val in values]


def _get_approval_request_type_options():
    return [{"value": 1, "label": "Remove"}, {"value": 2, "label": "Change Sr. No."}]


def _get_service_life_options():
    values = list(
        ShipEquipment.objects.exclude(service_life__isnull=True)
        .exclude(service_life="")
        .values_list("service_life", flat=True)
        .distinct()
        .order_by("service_life")
    )
    return [{"value": val, "label": f"{val} Years"} for val in values]


def _get_approval_status_options():
    return [
        {"value": 1, "label": "approved"},
        {"value": 2, "label": "Pending"},
        {"value": 3, "label": "Rejected"},
    ]


FILTER_OPTIONS_REGISTRY = {
    "equipment_name": _get_equipment_names,
    "sfd_category": _get_sfd_categories,
    "transaction_type": _get_transaction_types,
    "department": _get_departments,
    "sub_department": _get_sfd_list_sub_departments,
    "system": _get_system_options,
    "supplier": _get_suppliers,
    "oem": _get_oems,
    "compartment": _get_compartment_options,
    "qty_fitted": _get_qty_fitted_options,
    "location_code": _get_location_code_options,
    "location": _get_location_code_options,
    "remove_authority": _get_remove_authority_options,
    "remove_status": _get_remove_status_options,
    "approval_request_type": _get_approval_request_type_options,
    "service_life": _get_service_life_options,
    "approval_status": _get_approval_status_options,
}


class ReportFilterOptionsAPIView(APIView):
    def get(self, request):
        raw_fields = request.query_params.get("fields")
        if not raw_fields:
            return Response(
                {"fields": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        requested_keys = [k.strip() for k in raw_fields.split(",") if k.strip()]
        invalid = [k for k in requested_keys if k not in FILTER_OPTIONS_REGISTRY]
        if invalid or not requested_keys:
            return Response(
                {"fields": [f"Select a valid choice. {invalid} is not one of them."]}
                if invalid
                else {"fields": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({key: FILTER_OPTIONS_REGISTRY[key]() for key in requested_keys})


class SFDListFilterOptionsAPIView(ReportFilterOptionsAPIView):
    default_fields = ("equipment_name", "nomenclature", "sub_dept", "maintop_id")

    def get(self, request):
        _ = request
        registry = {
            "equipment_name": _get_equipment_names,
            "nomenclature": _get_sfd_list_nomenclatures,
            "sub_dept": _get_sfd_list_sub_departments,
            "maintop_id": _get_sfd_list_maintops,
        }
        return Response({key: registry[key]() for key in self.default_fields})


class ApprovalTrackingAPIView(APIView):
    STATUS_MAPPING = {1: "Pending", 2: "Approved", 3: "Returned"}

    def get(self, request):
        response = []

        remove_requests = RemoveEquipment.objects.select_related(
            "equipment", "ship_equipment"
        ).order_by("-created_at")
        for obj in remove_requests:
            response.append(
                {
                    "request_id": str(obj.pk),
                    "equipment": getattr(obj.equipment, "equipment_code", "") or "",
                    "category": "Remove",
                    "submitted_by": None,
                    "submitted": obj.created_at,
                    "status": self.STATUS_MAPPING.get(obj.approved_reject, "Pending"),
                    "insma_officer": "",
                    "insma_remarks": obj.removal_remark,
                }
            )

        change_requests = ChangeEquipmentRequest.objects.select_related(
            "equipment", "ship_equipment"
        ).order_by("-created_at")
        for obj in change_requests:
            response.append(
                {
                    "request_id": obj.universal_id_t_sfd_change_request or str(obj.pk),
                    "equipment": getattr(obj.equipment, "equipment_code", "") or "",
                    "category": "Change",
                    "submitted_by": obj.universal_id_a_user_created_by,
                    "submitted": obj.created_at,
                    "status": self.STATUS_MAPPING.get(obj.approved_reject, "Pending"),
                    "insma_officer": "",
                    "insma_remarks": "",
                }
            )

        response.sort(
            key=lambda x: x["submitted"] or timezone.make_aware(datetime.min),
            reverse=True,
        )
        return Response(response)

    def put(self, request):
        """Resubmit a "Returned" approval request with corrected details.
        `request_id` is a query param (matches the frontend's ApprovalTrackingUpdatePayload
        contract); resets the request back to Pending for re-review."""
        request_id = request.query_params.get("request_id")
        if not request_id:
            return Response(
                {"detail": "request_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = request.data.get("category")
        insma_remarks = request.data.get("insma_remarks")
        amendment_note = request.data.get("amendment_note")

        if category == "Remove":
            obj = RemoveEquipment.objects.filter(pk=request_id).first()
            if not obj:
                return Response(
                    {"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND
                )
            update_fields = ["approved_reject", "updated_at"]
            obj.approved_reject = None
            if insma_remarks is not None:
                obj.removal_remark = insma_remarks
                update_fields.append("removal_remark")
            if amendment_note is not None:
                obj.amendment_note = amendment_note
                update_fields.append("amendment_note")
            obj.save(update_fields=update_fields)
            data = {"request_id": str(obj.pk)}
        elif category == "Change":
            obj = (
                ChangeEquipmentRequest.objects.filter(
                    universal_id_t_sfd_change_request=request_id
                ).first()
                or ChangeEquipmentRequest.objects.filter(pk=_to_int(request_id)).first()
            )
            if not obj:
                return Response(
                    {"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND
                )
            update_fields = ["approved_reject", "updated_at"]
            obj.approved_reject = None
            if amendment_note is not None:
                obj.amendment_note = amendment_note
                update_fields.append("amendment_note")
            obj.save(update_fields=update_fields)
            data = {"request_id": obj.universal_id_t_sfd_change_request or str(obj.pk)}
        else:
            return Response(
                {"detail": "category must be 'Remove' or 'Change'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "Approval request resubmitted successfully.", "data": data}
        )


class ReportExportAPIView(APIView):
    def post(self, request, report_key):
        # `format`/`export_format` select PDF vs Excel — everything else in the body is a report
        # filter, forwarded to the Celery task as-is (same param names the report's own
        # filterset_class already expects, since the frontend builds this from the exact same
        # filter-param map the on-screen grid uses — see buildExportFilterParams()).
        export_format = (
            request.data.get("export_format")
            or request.data.get("format")
            or ReportExportJob.ExportFormat.EXCEL
        )
        filters = {
            key: value
            for key, value in request.data.items()
            if key not in ("format", "export_format")
        }

        job = ReportExportJob.objects.create(
            report_key=report_key,
            export_format=export_format,
            status=ReportExportJob.Status.PENDING,
        )

        from .tasks import generate_report_export_task

        generate_report_export_task.delay(str(job.id), filters)

        return Response(
            ReportExportJobSerializer(job).data, status=status.HTTP_201_CREATED
        )


class ReportExportJobStatusAPIView(generics.RetrieveAPIView):
    serializer_class = ReportExportJobSerializer

    queryset = ReportExportJob.objects.all()
    lookup_url_kwarg = "job_id"


class ReportExportJobDownloadAPIView(generics.RetrieveAPIView):
    serializer_class = ReportExportJobSerializer
    queryset = ReportExportJob.objects.all()
    lookup_url_kwarg = "job_id"

    def retrieve(self, request, *args, **kwargs):
        import os

        from django.conf import settings as django_settings
        from django.http import FileResponse

        job = self.get_object()

        if job.status != ReportExportJob.Status.SUCCESS or not job.file_path:
            return Response(
                {
                    "status": "error",
                    "message": job.error or "Export is not ready yet.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        absolute_path = os.path.join(django_settings.MEDIA_ROOT, job.file_path)
        if not os.path.exists(absolute_path):
            return Response(
                {"status": "error", "message": "Export file is missing."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_pdf = job.export_format == ReportExportJob.ExportFormat.PDF
        content_type = (
            "application/pdf"
            if is_pdf
            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        extension = "pdf" if is_pdf else "xlsx"

        response = FileResponse(open(absolute_path, "rb"), content_type=content_type)
        response["Content-Disposition"] = (
            f'attachment; filename="{job.report_key}.{extension}"'
        )
        return response


class SFDOverviewAPIView(APIView):
    def get(self, request):
        today = timezone.localdate()
        equipment_qs = _ship_equipment_queryset().select_related(
            "department", "sub_department_f_key", "ship", "equipment_category"
        )
        total = equipment_qs.count()
        mapped = equipment_qs.filter(
            Q(mapping_status="mapped") | Q(system__isnull=False)
        ).count()
        active = equipment_qs.filter(active=True).count()
        unmapped = max(total - mapped, 0)
        pending_approvals = RemoveEquipment.objects.filter(
            approved_reject__isnull=True
        ).count()

        six_months_ago = today - timedelta(days=183)
        one_year_ago = today - timedelta(days=365)
        two_years_ago = today - timedelta(days=730)

        def count_for(qs, since=None):
            if since is None:
                return qs.count()
            return qs.filter(created_at__date__gte=since).count()

        def trend_text(current, previous):
            if previous <= 0:
                return "+100%" if current > 0 else "0%"
            change = round(((current - previous) / previous) * 100)
            return f"{change:+d}%"

        def kpi(key, title, qs, count, subtitle, section_title, mode="breakdown"):
            last_30 = count_for(qs, today - timedelta(days=30))
            prev_30 = qs.filter(
                created_at__date__gte=today - timedelta(days=60),
                created_at__date__lt=today - timedelta(days=30),
            ).count()
            breakdown = self._department_breakdown(qs, total=count)
            return {
                "key": key,
                "title": title,
                "count": count,
                "displayValue": f"{count:,}",
                "iconColor": "",
                "iconBg": "",
                "iconPath": "",
                "trendUp": last_30 >= prev_30,
                "baseUp": last_30 >= prev_30,
                "selectedPeriod": "all",
                "trendData": {
                    "all": trend_text(last_30, prev_30),
                    "6m": trend_text(count_for(qs, six_months_ago), last_30),
                    "1y": trend_text(count_for(qs, one_year_ago), last_30),
                    "2y": trend_text(count_for(qs, two_years_ago), last_30),
                },
                "valueData": {
                    "all": f"{count:,}",
                    "6m": f"{count_for(qs, six_months_ago):,}",
                    "1y": f"{count_for(qs, one_year_ago):,}",
                    "2y": f"{count_for(qs, two_years_ago):,}",
                },
                "drawerSubtitle": subtitle,
                "sectionTitle": section_title,
                "sectionHint": "Units - Share",
                "stats": [
                    {"value": f"{count:,}", "label": "Total"},
                    {"value": f"{last_30:,}", "label": "Last 30 days"},
                    {"value": f"{mapped:,}", "label": "Mapped"},
                    {"value": f"{unmapped:,}", "label": "Unmapped"},
                ],
                "mode": mode,
                "breakdown": breakdown,
                "listRows": [],
            }

        all_kpis = [
            kpi(
                "total_equipment",
                "Total Equipment",
                equipment_qs,
                total,
                "current fleet total",
                "Equipment by department",
            ),
            kpi(
                "active_equipment",
                "Active Equipment",
                equipment_qs.filter(active=True),
                active,
                "active fitted equipment",
                "Active equipment by department",
            ),
            kpi(
                "mapped_equipment",
                "Mapped Equipment",
                equipment_qs.filter(
                    Q(mapping_status="mapped") | Q(system__isnull=False)
                ),
                mapped,
                "linked to system hierarchy",
                "Mapped equipment by department",
            ),
            {
                **kpi(
                    "pending_approvals",
                    "Pending Approvals",
                    equipment_qs.filter(status__icontains="progress"),
                    pending_approvals,
                    "awaiting action",
                    "Pending approval records",
                    mode="list",
                ),
                "count": pending_approvals,
                "displayValue": f"{pending_approvals:,}",
                "listRows": self._pending_approval_rows(),
            },
        ]

        dept_dist, dept_subs = self._department_distribution(equipment_qs)
        cat_segments = self._category_segments(equipment_qs)
        install_labels, install_series, install_legend = self._installation_trend(
            equipment_qs, today
        )

        return Response(
            {
                "allKpis": all_kpis,
                "alerts": self._alerts(pending_approvals, unmapped),
                "deptDist": dept_dist,
                "deptSubs": dept_subs,
                "catSegments": cat_segments,
                "catSummary": f"{total:,} fitted equipment records across {len(cat_segments)} categories",
                "installLabels": install_labels,
                "installSeries": install_series,
                "installLegend": install_legend,
                "activity": self._recent_activity(equipment_qs, today),
                "metadata": {
                    "lastSync": timezone.now().strftime("%d %B %Y, %I:%M %p"),
                    "generatedAt": timezone.now().isoformat(),
                    "version": "V1.0",
                },
                "total_equipment": total,
                "active_equipment": active,
                "mapped_equipment": mapped,
                "unmapped_equipment": unmapped,
                "pending_approvals": pending_approvals,
            }
        )

    def _department_breakdown(self, qs, total):
        rows = []
        max_count = max(total, 1)
        for row in (
            qs.values("department__name")
            .annotate(value=Count("id"))
            .order_by("-value", "department__name")[:8]
        ):
            name = row["department__name"] or "Unassigned"
            value = row["value"]
            rows.append(
                {
                    "name": name,
                    "pct": round((value / max_count) * 100),
                    "metrics": [
                        {"label": "Units", "value": f"{value:,}"},
                        {
                            "label": "Share",
                            "value": f"{round((value / max_count) * 100)}%",
                        },
                    ],
                    "equipments": [],
                }
            )
        return rows

    def _department_distribution(self, qs):
        rows = list(
            qs.values("department__name")
            .annotate(value=Count("id"))
            .order_by("-value", "department__name")
        )
        max_value = max([row["value"] for row in rows] or [0])
        dept_dist = [
            {
                "label": row["department__name"] or "Unassigned",
                "value": row["value"],
                "primary": row["value"] == max_value and max_value > 0,
            }
            for row in rows
        ]

        dept_subs = {}
        sub_rows = (
            qs.values("department__name", "sub_department_f_key__name")
            .annotate(value=Count("id"))
            .order_by("department__name", "-value", "sub_department_f_key__name")
        )
        for row in sub_rows:
            dept = row["department__name"] or "Unassigned"
            sub = row["sub_department_f_key__name"] or "Unassigned"
            dept_subs.setdefault(dept, []).append(
                {"label": sub, "short": sub, "value": row["value"]}
            )
        return dept_dist, dept_subs

    def _category_segments(self, qs):
        colors = ["#4AA8FF", "#22C55E", "#F59E0B", "#A855F7", "#14B8A6"]
        category_labels = dict(ShipEquipment.TransactionCategory.choices)
        rows = list(
            qs.values("category")
            .annotate(value=Count("id"))
            .order_by("-value", "category")
        )
        if not rows:
            return []
        return [
            {
                "label": category_labels.get(
                    row["category"], row["category"] or "Unassigned"
                ),
                "value": row["value"],
                "color": colors[index % len(colors)],
            }
            for index, row in enumerate(rows)
        ]

    def _installation_trend(self, qs, today):
        labels = []
        fitted_values = []
        mapped_values = []
        active_values = []
        start_month = date(today.year, today.month, 1)
        months = []
        for offset in range(5, -1, -1):
            month = start_month.month - offset
            year = start_month.year
            while month <= 0:
                month += 12
                year -= 1
            months.append(date(year, month, 1))

        for month_start in months:
            next_month = (
                date(month_start.year + 1, 1, 1)
                if month_start.month == 12
                else date(month_start.year, month_start.month + 1, 1)
            )
            month_qs = qs.filter(
                created_at__date__gte=month_start,
                created_at__date__lt=next_month,
            )
            labels.append(month_start.strftime("%b"))
            fitted_values.append(month_qs.count())
            mapped_values.append(
                month_qs.filter(
                    Q(mapping_status="mapped") | Q(system__isnull=False)
                ).count()
            )
            active_values.append(month_qs.filter(active=True).count())

        series = [
            {
                "label": "Fitted",
                "color": "#4AA8FF",
                "values": fitted_values,
                "area": True,
            },
            {"label": "Mapped", "color": "#22C55E", "values": mapped_values},
            {"label": "Active", "color": "#F59E0B", "values": active_values},
        ]
        legend = [
            {
                "label": item["label"],
                "value": sum(item["values"]),
                "color": item["color"],
            }
            for item in series
        ]
        return labels, series, legend

    def _recent_activity(self, qs, today):
        items = qs.order_by("-updated_at", "-created_at", "-id")[:20]
        return [_build_activity_row(item, today) for item in items]

    def _pending_approval_rows(self):
        rows = []
        pending = RemoveEquipment.objects.select_related(
            "equipment", "ship_equipment"
        ).filter(approved_reject__isnull=True)[:10]
        for item in pending:
            rows.append(
                {
                    "title": getattr(item.equipment, "equipment_code", None)
                    or "Removal Request",
                    "sub": item.removal_remark or "Pending approval",
                    "meta": item.created_at.strftime("%d %b %Y")
                    if item.created_at
                    else "",
                    "tag": "In Progress",
                    "tagColor": "#F59E0B",
                    "dotColor": "#F59E0B",
                }
            )
        return rows

    def _alerts(self, pending_approvals, unmapped):
        alerts = []
        if pending_approvals:
            alerts.append(
                {
                    "text": f"{pending_approvals} SFD approval request(s) pending",
                    "tag": "In Progress",
                    "color": "#F59E0B",
                }
            )
        if unmapped:
            alerts.append(
                {
                    "text": f"{unmapped} equipment record(s) not mapped to a system",
                    "tag": "Master",
                    "color": "#F82C36",
                }
            )
        return alerts


class SFDOverviewActivityAPIView(APIView):
    """Period-aware, paginated version of the Overview's 'Recently Added,
    Updated or Removed Equipment' feed. Unlike `SFDOverviewAPIView`'s
    `activity` field (a fixed teaser of the latest 20 rows regardless of
    period), this endpoint actually queries the requested period from the
    DB and paginates it, so Quarter/Year can surface more than 20 rows.
    """

    def get(self, request):
        today = timezone.localdate()
        period = (request.query_params.get("period") or "month").strip().lower()
        days = ACTIVITY_PERIOD_DAYS.get(period, ACTIVITY_PERIOD_DAYS["month"])
        cutoff = today - timedelta(days=days)

        qs = (
            _ship_equipment_queryset()
            .select_related("department", "ship", "equipment")
            .annotate(activity_at=Coalesce("updated_at", "created_at"))
            .filter(activity_at__date__gte=cutoff)
            .order_by("-activity_at", "-id")
        )
        rows = [_build_activity_row(item, today) for item in qs]
        return _paginated_response(request, rows)


class RecentActivityAPIView(APIView):
    """Recent Activity popup (SFD Management header) — ported from cs_swmm_v1's
    RecentActivityAPIView. `RawRecentActivityRow` on the frontend (tag/date/equipment/
    createdby/code/others) is the confirmed response contract."""

    @staticmethod
    def _equipment_name(tx):
        if tx is None:
            return ""
        if tx.type == ShipEquipment.TransactionType.EQUIPMENT:
            return (
                (tx.equipment.equipment_name if tx.equipment else None)
                or tx.new_equipment_name
                or ""
            )
        return (
            (tx.system.equipment_name if tx.system else None)
            or tx.new_system_name
            or ""
        )

    @staticmethod
    def _profile_display_name(profile):
        rank_name = getattr(getattr(profile, "rank", None), "name", None) or ""
        first = getattr(profile, "firstname", None) or "Yogesh"
        last = getattr(profile, "lastname", None) or "Chauhan"
        return f"{rank_name} {first} {last}".strip()

    def _build_activity(self, *, tag, transaction, created_by, code, others):
        return {
            "tag": tag,
            "date": transaction.created_at,
            "equipment": self._equipment_name(transaction),
            "createdby": created_by,
            "code": code or "",
            "others": others or "",
        }

    def _add_activities(
        self,
        activities,
        queryset,
        *,
        tag,
        transaction_getter,
        created_by_getter,
        code_getter,
        others_getter,
    ):
        activities.extend(
            self._build_activity(
                tag=tag,
                transaction=transaction_getter(obj),
                created_by=created_by_getter(obj),
                code=code_getter(obj),
                others=others_getter(obj),
            )
            for obj in queryset
        )

    @staticmethod
    def _section_name(tx):
        if tx.sub_department_f_key:
            return tx.sub_department_f_key.name
        return tx.equipment_section or ""

    def get(self, request):
        ship_id = request.query_params.get("ship_id")
        if not ship_id:
            return Response(
                {"detail": "ship_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            days = int(request.query_params.get("days", 30))
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            return Response(
                {"detail": "days and limit must be integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if days <= 0 or limit <= 0:
            return Response(
                {"detail": "days and limit must be greater than 0."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cutoff = timezone.now() - timedelta(days=days)
        activities = []

        # Added — a brand-new CAT III (New Induction) equipment row.
        added = ShipEquipment.objects.select_related(
            "equipment", "system", "created_by"
        ).filter(
            ship_id=ship_id,
            category=ShipEquipment.TransactionCategory.CAT3,
            active=True,
            created_at__gte=cutoff,
        )
        self._add_activities(
            activities,
            added,
            tag="Added",
            transaction_getter=lambda obj: obj,
            created_by_getter=lambda obj: self._profile_display_name(obj.created_by),
            code_getter=lambda obj: obj.equipment_serial_no or obj.new_equipment_sr_no,
            others_getter=lambda obj: self._section_name(obj),
        )

        # Removed — an approved removal request (request_type=1, matching remove()'s create call).
        removed = RemoveEquipment.objects.select_related(
            "ship_equipment__equipment",
            "ship_equipment__system",
            "ship_equipment__created_by",
        ).filter(
            ship_equipment__ship_id=ship_id,
            request_type=1,
            approved_reject=2,
            created_at__gte=cutoff,
        )
        self._add_activities(
            activities,
            removed,
            tag="Removed",
            transaction_getter=lambda obj: obj.ship_equipment,
            created_by_getter=lambda obj: self._profile_display_name(
                obj.ship_equipment.created_by
            ),
            code_getter=lambda obj: obj.equipment_serial_no,
            others_getter=lambda obj: obj.removal_remark,
        )

        # Submitted (Remove/Change Serial) — awaiting INSMA approval.
        submitted_remove = RemoveEquipment.objects.select_related(
            "ship_equipment__equipment",
            "ship_equipment__system",
            "ship_equipment__created_by",
        ).filter(
            ship_equipment__ship_id=ship_id,
            approved_reject__isnull=True,
            created_at__gte=cutoff,
        )
        self._add_activities(
            activities,
            submitted_remove,
            tag="Submitted",
            transaction_getter=lambda obj: obj.ship_equipment,
            created_by_getter=lambda obj: self._profile_display_name(
                obj.ship_equipment.created_by
            ),
            code_getter=lambda obj: obj.equipment_serial_no or "",
            others_getter=lambda obj: "Sent for INSMA Approval",
        )

        # Submitted (Change — CAT I/II/III record amendment) — awaiting INSMA approval.
        submitted_change = ChangeEquipmentRequest.objects.select_related(
            "ship_equipment__equipment", "ship_equipment__system"
        ).filter(
            ship_equipment__ship_id=ship_id,
            approved_reject__isnull=True,
            created_at__gte=cutoff,
        )
        self._add_activities(
            activities,
            submitted_change,
            tag="Submitted",
            transaction_getter=lambda obj: obj.ship_equipment,
            created_by_getter=lambda obj: obj.universal_id_a_user_created_by
            or "Yogesh Chauhan",
            code_getter=lambda obj: obj.ship_equipment.equipment_serial_no
            or obj.ship_equipment.new_equipment_sr_no,
            others_getter=lambda obj: "Sent for INSMA Approval",
        )

        activities.sort(
            key=lambda item: item["date"] or timezone.make_aware(datetime.min),
            reverse=True,
        )
        return Response(activities[:limit])


class ConvertEquipmentToSystemAPIView(APIView):
    def post(self, request):
        tx = get_object_or_404(
            ShipEquipment, pk=request.data.get("equipment_id") or request.data.get("id")
        )
        tx.is_system = True
        tx.type = ShipEquipment.TransactionType.SYSTEM
        tx.save(update_fields=["is_system", "type"])
        return Response(SourceShipEquipmentSerializer(tx).data)


class ConvertSystemToEquipmentAPIView(APIView):
    def post(self, request):
        tx = get_object_or_404(
            ShipEquipment, pk=request.data.get("equipment_id") or request.data.get("id")
        )
        tx.is_system = False
        tx.type = ShipEquipment.TransactionType.EQUIPMENT
        tx.save(update_fields=["is_system", "type"])
        return Response(SourceShipEquipmentSerializer(tx).data)


class SupplierListAPIView(APIView):
    def get(self, request):
        suppliers = Supplier.objects.filter(
            supplier_manufacture=1, active="1"
        ).order_by("id")
        data = [
            {
                "supplier_id": s.id,
                "supplier_code": _first_value(s.supplier_code, s.SupplierCode),
                "supplier_name": _supplier_display(s),
                "address": getattr(s, "address", None),
                "country_code": getattr(s, "CountryCode", None),
                "contact_number": getattr(s, "Contact_Number", None),
                "email_id": getattr(s, "Email_ID", None),
                "universal_id_M_supplier": getattr(s, "Universal_ID_M_Supplier", None),
                "universal_id_M_country": getattr(s, "Universal_ID_M_Country", None),
            }
            for s in suppliers
        ]
        return _paginated_response(request, data)


class ManufacturerListAPIView(APIView):
    def get(self, request):
        manufacturers = Supplier.objects.filter(
            supplier_manufacture=2, active="1"
        ).order_by("id")
        data = [
            {
                "manufacturer_id": s.id,
                "manufacturer_code": _first_value(s.supplier_code, s.SupplierCode),
                "manufacturer_name": _supplier_display(s),
                "address": getattr(s, "address", None),
                "country_code": getattr(s, "CountryCode", None),
                "contact_number": getattr(s, "Contact_Number", None),
                "email_id": getattr(s, "Email_ID", None),
                "universal_id_M_manufacturer": getattr(
                    s, "Universal_ID_M_Supplier", None
                ),
                "universal_id_M_country": getattr(s, "Universal_ID_M_Country", None),
            }
            for s in manufacturers
        ]
        return _paginated_response(request, data)


class EquipmentListAPIView(APIView):
    def get(self, request):
        return ReferenceEquipmentMasterListAPIView().list(request)


class SystemListAPIView(EquipmentListAPIView):
    pass
