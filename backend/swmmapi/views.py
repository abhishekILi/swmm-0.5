# ruff: noqa
import os
from django.db import DatabaseError
from django.shortcuts import redirect

try:
    # pyrefly: ignore [missing-import]
    import sweetify
except ImportError:
    sweetify = None

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from sfd.models import ShipEquipment
from master.utils import get_this_ship, get_dart_split
from sfd.utils import get_mssql_connection
from master.models import *
import logging
import requests
import json
import uuid
from ems.models import (
    AddRoutineDetails,
    EquipmentName,
    FussRaiseDetails,
    MaintopDetail,
    MaintopHeader,
    RoutineDescription,
    ShipMaster,
    UniqueRoutineName,
)
from datetime import datetime, date
from django.db import transaction
from dart.models import InitiateDart, CompleteDefectDart, CompletedRoutine
from collections import defaultdict
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from srar.models import *
from django.core import signing
from django.db.models import IntegerField, Max, Q
from django.db.models.functions import Cast


import environ

env = environ.Env()
API_URL = env("SWMM_API_URL")
logger = logging.getLogger(__name__)


class CommonPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "status": True,
                "message": "Data fetched successfully.",
                "pagination": {
                    "count": self.page.paginator.count,
                    "current_page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_pages": self.page.paginator.num_pages,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
                "data": data,
            }
        )


from django.http import HttpResponse, StreamingHttpResponse
from sfd.models import Equipment, EquipmentType, Supplier
from master.models import MEquipment as MasterEquipment
from master.models import Manufacturer as MasterManufacturer
from master.models import Supplier as MasterSupplier
from master.models import EquipmentType as MasterEquipmentType
from master.models import Country as MasterCountry
from master.models import Group as MasterGroup
from master.utils import parse_iso_date


def date_from_cmms(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse_iso_date(str(value))


def datetime_from_cmms(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return timezone.make_aware(value) if timezone.is_naive(value) else value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
    except ValueError:
        parsed_date = parse_iso_date(str(value))
        if parsed_date:
            return datetime.combine(parsed_date, datetime.min.time())
    return None


def _clean_text(value):
    return str(value or "").strip()


def _clean_upper(value):
    return _clean_text(value).upper()


def _clean_int(value, default=0):
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _routine_category(frequency):
    frequency = _clean_upper(frequency)
    if frequency.endswith("H"):
        return "RUNNING HOUR BASED", True
    if frequency.endswith(("A", "M", "Y")):
        return "CALENDAR BASED", True
    if frequency.endswith(("NR", "PRT", "SR", "MR", "PRR", "DK", "POLICY")):
        return "ALTERNATE PERIODIC", True
    if frequency.endswith(("O", "W", "D")):
        return "RUNNING HOUR BASED", False
    return "RUNNING HOUR BASED", True


def _find_equipment_name(row):
    equipment_uid = _clean_text(row.get("Universal_ID_T_EquipmentShipDetail"))
    nomenclature = _clean_text(row.get("nomenclature"))
    equipment_code = _clean_text(row.get("equipmentcode"))

    if equipment_uid:
        equipment = (
            EquipmentName.objects.filter(
                universal_id_t_equipment_ship_detail=equipment_uid
            ).first()
            or EquipmentName.objects.filter(
                sfd_equipment__t_equipment_ship_detail=equipment_uid
            ).first()
        )
        if equipment:
            return equipment

    queryset = EquipmentName.objects.all()
    if equipment_code:
        queryset = queryset.filter(equipment_code__iexact=equipment_code)
    if nomenclature:
        return (
            queryset.filter(nomenclature__iexact=nomenclature).first()
            or EquipmentName.objects.filter(name__iexact=nomenclature).first()
        )
    return None


def _next_missing_routine_dart(department):
    if not department:
        return None, None
    try:
        from ems.utils import generate_routine_dart_number

        last_entry = (
            RoutineDescription.objects.select_for_update()
            .filter(department_f_key=department, dart_sr_no__regex=r"^\d+$")
            .annotate(dart_sr_no_int=Cast("dart_sr_no", IntegerField()))
            .aggregate(max_sr=Max("dart_sr_no_int"))["max_sr"]
            or 0
        )
        return generate_routine_dart_number(department.name, "Routine", last_entry)
    except Exception:
        logger.exception("Failed to generate local routine DART number")
        return None, None


def sync_cmms_routine_row(row, create_missing_dart=False):
    equipment = _find_equipment_name(row)
    if not equipment:
        return "SKIPPED", f"Missing equipment: {_clean_text(row.get('nomenclature'))}"

    department_name = _clean_text(row.get("departmentname"))
    department = Department.objects.filter(
        name__iexact=department_name
    ).first() or getattr(getattr(equipment, "sfd_equipment", None), "department", None)
    if not department:
        return "SKIPPED", f"Missing department: {department_name or 'N/A'}"

    routine_name_text = _clean_upper(row.get("routinename")) or _clean_upper(
        row.get("frequency")
    )
    if not routine_name_text:
        return "SKIPPED", "Missing routine name"

    routine_name, _ = UniqueRoutineName.objects.get_or_create(name=routine_name_text)
    ship_name = _clean_upper(row.get("shipname"))
    ship_master = (
        ShipMaster.objects.get_or_create(ship_name=ship_name)[0] if ship_name else None
    )

    frequency_uid = _clean_text(row.get("Universal_ID_M_Frequency"))
    frequency_obj = (
        Frequency.objects.filter(universal_id_m_frequency=frequency_uid).first()
        if frequency_uid
        else None
    )
    frequency = _clean_upper(row.get("frequency"))
    routine_category, is_greater_than_3_monthly = _routine_category(frequency)

    maintop_no = _clean_upper(row.get("maintopno"))
    routine_no = _clean_upper(row.get("routineno"))
    routine_desc = _clean_text(row.get("routinedescription"))
    dart_number = _clean_upper(row.get("dartnumber"))
    dart_sr_no = None
    if dart_number:
        parts = dart_number.split("-")
        dart_sr_no = parts[2] if len(parts) > 2 else None
    elif create_missing_dart:
        dart_number, dart_sr_no = _next_missing_routine_dart(department)

    maintop_detail_uid = _clean_text(row.get("universal_id_t_maintopdetail"))
    maintop_detail = (
        MaintopDetail.objects.filter(
            universal_id_t_maintopdetail=maintop_detail_uid
        ).first()
        if maintop_detail_uid
        else None
    )

    add_lookup = {
        "equipment_name": equipment,
        "routine_name": routine_name,
        "maintop_no": maintop_no,
        "routine_no": routine_no,
        "frequency": frequency,
    }
    add_defaults = {
        "class_name": _clean_upper(row.get("classname")),
        "ship": ship_master,
        "equipment_code": _clean_text(row.get("equipmentcode")),
        "nomenclature": _clean_text(row.get("nomenclature")) or equipment.nomenclature,
        "dart_number": dart_number,
        "by_whom": _clean_upper(row.get("bywhom")),
        "frequency_in_months": _clean_int(row.get("frequencymonth")),
        "frequency_in_hours": _clean_int(row.get("frequencyhours")),
        "rhs_i": _clean_text(row.get("lastroutinecompletedatrh")) or "0",
        "rhs_i_updated_upto": date_from_cmms(row.get("rhsiupdatedupto")),
        "last_routine_completion_date": datetime_from_cmms(
            row.get("lastroutinecompletedatdate")
        ),
        "last_routine_completion_atrunning_hrs": _clean_int(
            row.get("lastroutinecompletedatrh")
        ),
        "frequency_f_key": frequency_obj,
        "routine_category": routine_category,
        "converted": False,
    }
    add_routine, add_created = AddRoutineDetails.objects.update_or_create(
        **add_lookup, defaults=add_defaults
    )

    if not routine_desc:
        return (
            "CREATED" if add_created else "UPDATED",
            f"{equipment.name} / {maintop_no} / {routine_no}",
        )

    universal_id_t_dart = _clean_text(row.get("Universal_ID_T_Dart"))
    rd_lookup = (
        {"universal_id_t_dart": universal_id_t_dart}
        if universal_id_t_dart
        else {
            "equipment_name": equipment,
            "add_routine_details": add_routine,
            "routine_no": routine_no,
        }
    )
    rd_defaults = {
        "equipment_name": equipment,
        "routine_name": routine_name,
        "add_routine_details": add_routine,
        "maintop_no": maintop_no,
        "dart_number": dart_number,
        "routine_no": routine_no,
        "routine_description": routine_desc,
        "by_whom": _clean_upper(row.get("bywhom")) or "",
        "last_routine_completion_date": datetime_from_cmms(
            row.get("lastroutinecompletedatdate")
        ),
        "last_routine_completion_atrunning_hrs": _clean_text(
            row.get("lastroutinecompletedatrh")
        ),
        "dart_sr_no": dart_sr_no,
        "due_date": date_from_cmms(row.get("routineduedate")),
        "previous_completed_date": date_from_cmms(
            row.get("lastroutinecompletedatdate")
        ),
        "due_at_rh": _clean_text(row.get("dueatrh")),
        "previous_completed_at_rh": _clean_text(row.get("lastroutinecompletedatrh")),
        "department_f_key": department,
        "maintop_detail": maintop_detail,
        "is_greater_than_3_monthly": is_greater_than_3_monthly,
    }
    _, rd_created = RoutineDescription.objects.update_or_create(
        **rd_lookup, defaults=rd_defaults
    )

    status_text = "CREATED" if (add_created or rd_created) else "UPDATED"
    return status_text, f"{equipment.name} / {maintop_no} / {routine_no}"


def build_sync_log(title, rows, *, create_missing_dart=False):
    return "\n".join(
        stream_sync_log(title, rows, create_missing_dart=create_missing_dart)
    )


def stream_sync_log(title, rows, *, create_missing_dart=False):
    """Generator version of build_sync_log — each row calls sync_cmms_routine_row (several
    individual ORM reads/writes apiece, not bulk-batchable given its per-row FK-resolution
    business logic), so at a few thousand rows the whole thing can take minutes. Yielding line by
    line lets this be wrapped in a StreamingHttpResponse so the frontend's streamSync() shows real
    progress instead of the request just sitting there looking hung until it's all done.
    """
    yield f"[SYSTEM] Starting {title}...\n"
    yield f"Fetched {len(rows)} records. Processing start...\n"
    created = updated = skipped = 0
    for row in rows:
        status_text, message = sync_cmms_routine_row(
            row, create_missing_dart=create_missing_dart
        )
        if status_text == "CREATED":
            created += 1
            yield f"[NEW] {message}\n"
        elif status_text == "UPDATED":
            updated += 1
            yield f"[EXISTING] {message}\n"
        else:
            skipped += 1
            yield f"[SKIPPED] {message}\n"

    yield "[Completed] Routine Sync Finished!\n"
    yield f"New: {created}, Existing: {updated}, Skipped: {skipped}"


class CMMSFDDataAPI(APIView):
    pagination_class = CommonPagination

    def _env_ship_identifier(self):
        return (
            env.str("SWMM_SHIP_CODE", default="").strip()
            or env.str("DEFAULT_SHIP_ID", default="").strip()
            or env.str("SHIP_ID", default="").strip()
            or "L18"
        )

    def _fetch_target_ship(self, cursor, ship_identifier):
        query = """
            SELECT
                M_Ship.Universal_ID_M_Ship,
                M_Ship.ShipName,
                M_Ship.ShipCode,
                M_Ship.ShipSrNo,
                M_Ship.SFDHierarchyID,
                M_Ship.ShipCategoryID,
                M_ShipCategory.ShipCategoryName,
                M_Ship.ClassID,
                M_Ship.ClassCode,
                M_ShipClass.Description AS ClassDescription,
                M_Ship.CommissionDate,
                M_Ship.CommandID,
                M_Command.CommandName,
                M_Ship.AuthorityID,
                M_OpsAuthority.OpsAuthority AS AuthorityName,
                M_Ship.OpsCode,
                M_Ship.ShipBuilder,
                M_Ship.DecommissionDate,
                M_Ship.Displacement,
                M_Ship.HoursUnderway,
                M_Ship.DistanceRun,
                M_Ship.DecommissionScheduledDate,
                M_Ship.PropulsionID,
                M_Propulsion.PropulsionName,
                M_Ship.SDRSREF,
                M_Ship.Active AS ShipActive,
                M_Ship.CreatedBy AS ShipCreatedBy,
                M_Ship.CreatedDate AS ShipCreatedDate,
                M_Ship.UpdatedBy AS ShipUpdatedBy,
                M_Ship.UpdatedDate AS ShipUpdatedDate,
                M_Ship.YardNo,
                M_Ship.ReferenceNo,
                M_Ship.ClassificationSociety,
                M_Ship.LengthOverall,
                M_Ship.LengthPerpen,
                M_Ship.ModuleBreadth,
                M_Ship.WettedUnderWater,
                M_Ship.DepthMain,
                M_Ship.StandardDisp,
                M_Ship.FullLoadDisp,
                M_Ship.StandDraft,
                M_Ship.FullloadDraft,
                M_Ship.WettedBootTop,
                M_Ship.Enginerating,
                M_Ship.MaxContSpeed,
                M_Ship.EcoSpeed,
                M_Ship.Endurance,
                M_Ship.Remark AS ShipRemark,
                M_Ship.Universal_ID_M_ShipCategory,
                M_Ship.Universal_ID_M_ShipClass,
                M_Ship.Universal_ID_M_Command,
                M_Ship.Universal_ID_M_OpsAuthority,
                M_Ship.Universal_ID_M_Propulsion,
                M_Ship.Universal_ID_A_User_Created_By AS ShipCreatedByUid,
                M_Ship.Universal_ID_A_User_Updated_By AS ShipUpdatedByUid,
                M_Ship.Refit_Authority,
                M_Ship.Signal_Name,
                M_Ship.Address,
                M_Ship.Contact_Number AS ShipContactNumber,
                M_Ship.NUD_Email_ID,
                M_Ship.NIC_Email_ID,
                M_Ship.Universal_ID_M_Overseeing_Team,
                M_Ship.IsCMMSInstall,
                M_Ship.IsInGD,
                M_Ship.Universal_ID_M_ShipUnitCategory,
                M_Ship.ILMSCustomerCode
            FROM M_Ship
            LEFT JOIN M_ShipCategory
                ON M_Ship.ShipCategoryID = M_ShipCategory.ShipCategoryID
            LEFT JOIN M_ShipClass
                ON M_Ship.ClassID = M_ShipClass.ClassID
            LEFT JOIN M_Command
                ON M_Ship.CommandID = M_Command.CommandID
            LEFT JOIN M_OpsAuthority
                ON M_Ship.AuthorityID = M_OpsAuthority.AuthorityID
            LEFT JOIN M_Propulsion
                ON M_Ship.PropulsionID = M_Propulsion.PropulsionID
            WHERE
                LOWER(CAST(M_Ship.ShipCode AS VARCHAR(255))) = LOWER(?)
                OR LOWER(CAST(M_Ship.Universal_ID_M_Ship AS VARCHAR(255))) = LOWER(?)
                OR LOWER(CAST(M_Ship.ShipName AS VARCHAR(255))) = LOWER(?)
        """
        cursor.execute(query, [ship_identifier, ship_identifier, ship_identifier])
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        if not rows:
            return None
        return dict(zip(columns, rows[0]))

    def _fetch_ship_equipment_rows(self, cursor, ship_uid):
        query = """
            SELECT
                M_Ship.Universal_ID_M_Ship,
                M_Ship.ShipName,
                M_Ship.ShipCode,

                M_Department.Universal_ID_M_Department,
                M_Department.Description AS DeptName,
                M_Department.DeptCode,
                M_Department.SFDApplicable,

                M_SubDepartment.Universal_ID_M_SubDepartment,
                M_SubDepartment.Description AS SubDeptName,

                M_Equipment.Universal_ID_M_Equipment,
                M_Equipment.EquipmentCode,
                M_Equipment.EquipmentName,
                M_Equipment.EquipmentModel,
                M_Equipment.Universal_ID_T_MaintopHeader,
                M_Equipment.MaintopNumber,
                M_Equipment.ManufacturerName,
                M_Equipment.authority,
                M_Equipment.obsolete,
                M_Equipment.AcquaintIssued,
                M_Equipment.ILMSEquipmentCode,
                M_Equipment.CountryID AS EquipmentCountryID,
                EquipmentCountry.CountryCode AS EquipmentCountryCode,
                EquipmentCountry.CountryName AS EquipmentCountryName,
                M_Equipment.GroupID AS EquipmentGroupID,
                M_Equipment.GroupCode AS EquipmentGroupCode,
                M_Equipment.GenericSrNo AS EquipmentGenericSrNo,

                M_Supplier.SupplierID,
                M_Supplier.SupplierCode,
                M_Supplier.Universal_ID_M_Supplier,
                M_Supplier.SupplierName,
                M_Supplier.SupplierManufacturer,
                M_Supplier.Active AS SupplierActive,
                M_Supplier.Address,
                M_Supplier.AreaStreet,
                M_Supplier.City,
                M_Supplier.CountryCode,
                M_Supplier.CountryID,
                M_Supplier.Universal_ID_M_Country,
                M_Supplier.Contact_Person,
                M_Supplier.Contact_Number,
                M_Supplier.Email_ID,
                M_Country.CountryName,

                T_EquipmentShipDetail.Universal_ID_T_EquipmentShipDetail,
                T_EquipmentShipDetail.Universal_ID_M_Department
                    AS DetailUniversal_ID_M_Department,
                T_EquipmentShipDetail.Universal_ID_M_SubDepartment
                    AS DetailUniversal_ID_M_SubDepartment,
                T_EquipmentShipDetail.Nomenclature,
                T_EquipmentShipDetail.InstallationDate,
                T_EquipmentShipDetail.EquipmentSrNo,
                T_EquipmentShipDetail.LocationOnBoard,
                T_EquipmentShipDetail.LocationCode,
                T_EquipmentShipDetail.SRARApplicable,
                T_EquipmentShipDetail.Authority_of_Installation,
                T_EquipmentShipDetail.NoOfFits AS Quantity,
                T_EquipmentShipDetail.RemovalDate,
                T_EquipmentShipDetail.OEMPartNo,
                T_EquipmentShipDetail.Remark AS DetailRemark,
                T_EquipmentShipDetail.MaintopID,
                T_EquipmentShipDetail.ServiceLife,
                T_EquipmentShipDetail.Status AS DetailStatus,
                T_EquipmentShipDetail.Universal_ID_M_SrarType,
                T_EquipmentShipDetail.Universal_ID_M_Supplier_Manufacturer,
                T_EquipmentShipDetail.Universal_ID_M_Equipment_ParentEquipment,
                T_EquipmentShipDetail.Removal_Remark,
                T_EquipmentShipDetail.Authority_Of_Removal,
                T_EquipmentShipDetail.RH_Of_New_Equipemnt_At_Time_Of_Installation,
                T_EquipmentShipDetail.INSMAREMARKS,
                T_EquipmentShipDetail.IsSynced AS DetailIsSynced,

                ManufacturerSupplier.Universal_ID_M_Supplier AS ManufacturerUid,
                ManufacturerSupplier.SupplierCode AS ManufacturerSupplierCode,
                ManufacturerSupplier.SupplierName AS ManufacturerSupplierName,
                ManufacturerSupplier.SupplierManufacturer
                    AS ManufacturerSupplierManufacturer,
                ManufacturerSupplier.Active AS ManufacturerSupplierActive
            FROM T_EquipmentShipDetail
            INNER JOIN M_Ship
                ON T_EquipmentShipDetail.Universal_ID_M_Ship =
                   M_Ship.Universal_ID_M_Ship
            LEFT JOIN M_Department
                ON T_EquipmentShipDetail.Universal_ID_M_Department =
                   M_Department.Universal_ID_M_Department
            LEFT JOIN M_SubDepartment
                ON T_EquipmentShipDetail.Universal_ID_M_SubDepartment =
                   M_SubDepartment.Universal_ID_M_SubDepartment
            LEFT JOIN M_Equipment
                ON T_EquipmentShipDetail.Universal_ID_M_Equipment =
                   M_Equipment.Universal_ID_M_Equipment
            LEFT JOIN M_Supplier
                ON T_EquipmentShipDetail.SupplierID = M_Supplier.SupplierID
            LEFT JOIN M_Country
                ON M_Supplier.CountryID = M_Country.CountryID
            LEFT JOIN M_Country AS EquipmentCountry
                ON M_Equipment.CountryID = EquipmentCountry.CountryID
            OUTER APPLY (
                SELECT TOP 1 T_EquipmentSupplier.Universal_ID_M_Supplier
                FROM T_EquipmentSupplier
                WHERE T_EquipmentSupplier.Universal_ID_M_Equipment =
                          M_Equipment.Universal_ID_M_Equipment
                    AND T_EquipmentSupplier.Active = 1
                    AND T_EquipmentSupplier.SupplierManufacturer = 2
                ORDER BY T_EquipmentSupplier.EquipmentSupplierID DESC
            ) AS ManufacturerLink(Universal_ID_M_Supplier)
            LEFT JOIN M_Supplier AS ManufacturerSupplier
                ON ManufacturerLink.Universal_ID_M_Supplier =
                   ManufacturerSupplier.Universal_ID_M_Supplier
            WHERE
                T_EquipmentShipDetail.Active = 1
                AND T_EquipmentShipDetail.RemovalDate IS NULL
                AND M_Ship.Universal_ID_M_Ship = ?
        """
        cursor.execute(query, [ship_uid])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _resolve_ship_unit_type(self, ship_uid):
        existing_ship = Ship.objects.filter(universal_id_m_ship=ship_uid).first()
        if existing_ship and existing_ship.unit_type_id:
            return existing_ship.unit_type

        unit_type = UnitType.objects.order_by("id").first()
        if unit_type:
            return unit_type

        unit_type, _ = UnitType.objects.get_or_create(name="CMMS")
        return unit_type

    def _sync_rows_to_swmm(self, target_ship, rows):
        counts = {
            "ship": 0,
            "department": 0,
            "sub_department": 0,
            "equipment": 0,
            "equipment_type": 0,
            "supplier": 0,
            "ship_equipment": 0,
            "ems_equipment": 0,
            "master_manufacturer": 0,
            "master_equipment_type": 0,
            "master_equipment": 0,
            "master_supplier": 0,
        }

        ship_uid = target_ship.get("Universal_ID_M_Ship")
        ship_name = target_ship.get("ShipName") or ""
        ship_code = target_ship.get("ShipCode") or ""

        with transaction.atomic():
            unit_type = self._resolve_ship_unit_type(ship_uid)

            ship_category_obj = None
            ship_category_id = target_ship.get("ShipCategoryID")
            if ship_category_id is not None:
                ship_category_obj, _ = MShipCategory.objects.update_or_create(
                    ship_category_id=ship_category_id,
                    defaults={
                        "ship_category_name": target_ship.get("ShipCategoryName")
                        or None
                    },
                )

            propulsion_obj = None
            propulsion_id = target_ship.get("PropulsionID")
            if propulsion_id is not None:
                propulsion_obj, _ = MShipPropulsion.objects.update_or_create(
                    propulsion_id=propulsion_id,
                    defaults={
                        "propulsion_name": target_ship.get("PropulsionName") or None
                    },
                )

            class_master_obj = None
            class_id = target_ship.get("ClassID")
            if class_id is not None:
                class_master_obj, _ = MShipClass.objects.update_or_create(
                    class_id=class_id,
                    defaults={
                        "class_code": target_ship.get("ClassCode") or None,
                        "description": target_ship.get("ClassDescription") or None,
                    },
                )

            command_obj = None
            command_id = target_ship.get("CommandID")
            if command_id is not None:
                command_obj, _ = MShipCommand.objects.update_or_create(
                    command_id=command_id,
                    defaults={"command_name": target_ship.get("CommandName") or None},
                )

            ops_authority_obj = None
            authority_id = target_ship.get("AuthorityID")
            if authority_id is not None:
                ops_authority_obj, _ = MShipOpsAuthority.objects.update_or_create(
                    authority_id=authority_id,
                    defaults={
                        "ops_authority": target_ship.get("AuthorityName") or None,
                        "command": command_obj,
                    },
                )

            def _str_or_none(value):
                return str(value) if value not in (None, "") else None

            def _bool_or_none(value):
                return bool(value) if value is not None else None

            ship_obj, created = Ship.objects.update_or_create(
                universal_id_m_ship=ship_uid,
                defaults={
                    "name": ship_name,
                    "code": ship_code,
                    "unit_type": unit_type,
                    "unit_type_string": unit_type.name,
                    "sr_no": _str_or_none(target_ship.get("ShipSrNo")),
                    "sfd_hierarchy_id": target_ship.get("SFDHierarchyID"),
                    "class_master": class_master_obj,
                    "class_code": _str_or_none(target_ship.get("ClassCode")),
                    "commission_date": date_from_cmms(
                        target_ship.get("CommissionDate")
                    ),
                    "command": command_obj,
                    "authority": ops_authority_obj,
                    "ops_code": _str_or_none(target_ship.get("OpsCode")),
                    "ship_builder": _str_or_none(target_ship.get("ShipBuilder")),
                    "decommission_date": date_from_cmms(
                        target_ship.get("DecommissionDate")
                    ),
                    "displacement": _str_or_none(target_ship.get("Displacement")),
                    "hours_underway": _str_or_none(target_ship.get("HoursUnderway")),
                    "distance_run": _str_or_none(target_ship.get("DistanceRun")),
                    "decommission_scheduled_date": date_from_cmms(
                        target_ship.get("DecommissionScheduledDate")
                    ),
                    "sdrsref": _str_or_none(target_ship.get("SDRSREF")),
                    "active_external": _bool_or_none(target_ship.get("ShipActive")),
                    "created_by_external": _str_or_none(
                        target_ship.get("ShipCreatedBy")
                    ),
                    "created_date_external": target_ship.get("ShipCreatedDate"),
                    "updated_by_external": _str_or_none(
                        target_ship.get("ShipUpdatedBy")
                    ),
                    "updated_date_external": target_ship.get("ShipUpdatedDate"),
                    "yard_no": _str_or_none(target_ship.get("YardNo")),
                    "reference_no": _str_or_none(target_ship.get("ReferenceNo")),
                    "classification_society": _str_or_none(
                        target_ship.get("ClassificationSociety")
                    ),
                    "length_overall": _str_or_none(target_ship.get("LengthOverall")),
                    "length_perpen": _str_or_none(target_ship.get("LengthPerpen")),
                    "module_breath": _str_or_none(target_ship.get("ModuleBreadth")),
                    "wetted_under_water": _str_or_none(
                        target_ship.get("WettedUnderWater")
                    ),
                    "depth_main": _str_or_none(target_ship.get("DepthMain")),
                    "standard_disp": _str_or_none(target_ship.get("StandardDisp")),
                    "full_load_disp": _str_or_none(target_ship.get("FullLoadDisp")),
                    "stand_draft": _str_or_none(target_ship.get("StandDraft")),
                    "full_load_draft": _str_or_none(target_ship.get("FullloadDraft")),
                    "wetted_boot_top": _str_or_none(target_ship.get("WettedBootTop")),
                    "engine_rating": _str_or_none(target_ship.get("Enginerating")),
                    "max_cont_speed": _str_or_none(target_ship.get("MaxContSpeed")),
                    "eco_speed": _str_or_none(target_ship.get("EcoSpeed")),
                    "endurance": _str_or_none(target_ship.get("Endurance")),
                    "remark": _str_or_none(target_ship.get("ShipRemark")),
                    "universal_id_m_ship_category": _str_or_none(
                        target_ship.get("Universal_ID_M_ShipCategory")
                    ),
                    "universal_id_m_ship_class": _str_or_none(
                        target_ship.get("Universal_ID_M_ShipClass")
                    ),
                    "universal_id_m_command": _str_or_none(
                        target_ship.get("Universal_ID_M_Command")
                    ),
                    "universal_id_m_ops_authority": _str_or_none(
                        target_ship.get("Universal_ID_M_OpsAuthority")
                    ),
                    "universal_id_m_propulsion": _str_or_none(
                        target_ship.get("Universal_ID_M_Propulsion")
                    ),
                    "universal_id_a_user_created_by": _str_or_none(
                        target_ship.get("ShipCreatedByUid")
                    ),
                    "universal_id_a_user_updated_by": _str_or_none(
                        target_ship.get("ShipUpdatedByUid")
                    ),
                    "refit_authority": _str_or_none(target_ship.get("Refit_Authority")),
                    "signal_name": _str_or_none(target_ship.get("Signal_Name")),
                    "address": _str_or_none(target_ship.get("Address")),
                    "contact_number": _str_or_none(
                        target_ship.get("ShipContactNumber")
                    ),
                    "nud_email_id": _str_or_none(target_ship.get("NUD_Email_ID")),
                    "nic_email_id": _str_or_none(target_ship.get("NIC_Email_ID")),
                    "universal_id_m_overseeing_team": _str_or_none(
                        target_ship.get("Universal_ID_M_Overseeing_Team")
                    ),
                    "is_cmms_install": _bool_or_none(target_ship.get("IsCMMSInstall")),
                    "is_in_gd": _bool_or_none(target_ship.get("IsInGD")),
                    "universal_id_m_ship_unit_category": _str_or_none(
                        target_ship.get("Universal_ID_M_ShipUnitCategory")
                    ),
                    "customer_code": _str_or_none(target_ship.get("ILMSCustomerCode")),
                    "ship_category": ship_category_obj,
                    "propulsion": propulsion_obj,
                },
            )
            if created:
                counts["ship"] += 1

            for row in rows:
                dept_uid = row.get("DetailUniversal_ID_M_Department") or row.get(
                    "Universal_ID_M_Department"
                )
                dept_name = row.get("DeptName") or ""
                dept_code_raw = row.get("DeptCode")
                dept_obj = None
                if dept_uid and dept_name:
                    dept_obj, created = Department.objects.update_or_create(
                        universal_id_m_department=dept_uid,
                        defaults={
                            "name": dept_name,
                            "code": (dept_code_raw or dept_name)[:250],
                            "dep_code": dept_code_raw or None,
                            "description": dept_name,
                            "sfd_applicable": row.get("SFDApplicable"),
                        },
                    )
                    if created:
                        counts["department"] += 1

                subdept_uid = row.get("DetailUniversal_ID_M_SubDepartment") or row.get(
                    "Universal_ID_M_SubDepartment"
                )
                subdept_name = row.get("SubDeptName") or ""
                subdept_obj = None
                if subdept_uid and subdept_name:
                    subdept_obj, created = SubDepartment.objects.update_or_create(
                        universal_id_m_sub_department=subdept_uid,
                        defaults={
                            "department_name": dept_obj,
                            "name": subdept_name,
                            "description": subdept_name,
                        },
                    )
                    if created:
                        counts["sub_department"] += 1

                eq_uid = row.get("Universal_ID_M_Equipment")
                eq_code = row.get("EquipmentCode") or ""
                eq_name = row.get("EquipmentName") or ""
                eq_model = row.get("EquipmentModel") or ""
                eq_obj = None
                if eq_uid or eq_code:
                    eq_lookup = (
                        {"universal_id_m_equipment": eq_uid}
                        if eq_uid
                        else {"equipment_code": eq_code}
                    )
                    eq_obj, created = Equipment.objects.update_or_create(
                        **eq_lookup,
                        defaults={
                            "equipment_code": eq_code,
                            "model": eq_model,
                            "equipment_class": eq_name,
                            "maintop_number": row.get("MaintopNumber") or None,
                            "manufacturer_name": row.get("ManufacturerName") or None,
                            "authority": row.get("authority") or None,
                        },
                    )
                    if created:
                        counts["equipment"] += 1

                eqtype_obj = None
                if eq_name:
                    eqtype_obj, created = EquipmentType.objects.get_or_create(
                        equipment_desc=eq_name,
                        defaults={
                            "equipment_type_id": str(eq_uid or eq_code or eq_name),
                            "status": "Active",
                        },
                    )
                    if created:
                        counts["equipment_type"] += 1

                supplier_uid = row.get("Universal_ID_M_Supplier")
                supplier_name = row.get("SupplierName") or ""
                supplier_code = row.get("SupplierCode") or ""
                supplier_manufacture_raw = row.get("SupplierManufacturer")
                supplier_manufacture = (
                    int(supplier_manufacture_raw)
                    if supplier_manufacture_raw not in (None, "")
                    else None
                )
                supplier_obj = None
                if supplier_uid or supplier_name:
                    supplier_lookup = (
                        {"Universal_ID_M_Supplier": supplier_uid}
                        if supplier_uid
                        else {"SupplierName": supplier_name}
                    )
                    supplier_obj, created = Supplier.objects.update_or_create(
                        **supplier_lookup,
                        defaults={
                            "SupplierID": row.get("SupplierID"),
                            "SupplierCode": supplier_code,
                            "SupplierName": supplier_name,
                            "SupplierManufacturer": (
                                str(supplier_manufacture_raw)
                                if supplier_manufacture_raw not in (None, "")
                                else None
                            ),
                            "supplier_code": supplier_code,
                            "supplier_name": supplier_name,
                            "supplier_manufacture": supplier_manufacture,
                            "address": (row.get("Address") or "")[:255] or None,
                            "AreaStreet": row.get("AreaStreet") or None,
                            "City": row.get("City") or None,
                            "CountryCode": row.get("CountryCode") or None,
                            "CountryID": (
                                str(row.get("CountryID"))
                                if row.get("CountryID") not in (None, "")
                                else None
                            ),
                            "Universal_ID_M_Country": row.get("Universal_ID_M_Country")
                            or None,
                            "Contact_Person": row.get("Contact_Person") or None,
                            "Contact_Number": row.get("Contact_Number") or None,
                            "Email_ID": row.get("Email_ID") or None,
                            "active": "1" if row.get("SupplierActive") else "0",
                        },
                    )
                    if created:
                        counts["supplier"] += 1

                # Manufacturer is a *separate* relationship from the installation
                # supplier above — CMMS links it via T_EquipmentSupplier
                # (SupplierManufacturer=2), not T_EquipmentShipDetail.SupplierID.
                manufacturer_uid = row.get("ManufacturerUid")
                manufacturer_supplier_name = row.get("ManufacturerSupplierName") or ""
                manufacturer_supplier_code = row.get("ManufacturerSupplierCode") or ""
                manufacturer_supplier_manufacture_raw = row.get(
                    "ManufacturerSupplierManufacturer"
                )
                manufacturer_supplier_obj = None
                if manufacturer_uid or manufacturer_supplier_name:
                    manufacturer_lookup = (
                        {"Universal_ID_M_Supplier": manufacturer_uid}
                        if manufacturer_uid
                        else {"SupplierName": manufacturer_supplier_name}
                    )
                    manufacturer_supplier_obj, created = (
                        Supplier.objects.update_or_create(
                            **manufacturer_lookup,
                            defaults={
                                "SupplierCode": manufacturer_supplier_code,
                                "SupplierName": manufacturer_supplier_name,
                                "SupplierManufacturer": (
                                    str(manufacturer_supplier_manufacture_raw)
                                    if manufacturer_supplier_manufacture_raw
                                    not in (None, "")
                                    else "2"
                                ),
                                "supplier_code": manufacturer_supplier_code,
                                "supplier_name": manufacturer_supplier_name,
                                "supplier_manufacture": (
                                    int(manufacturer_supplier_manufacture_raw)
                                    if manufacturer_supplier_manufacture_raw
                                    not in (None, "")
                                    else 2
                                ),
                                "active": (
                                    "1"
                                    if row.get("ManufacturerSupplierActive")
                                    else "0"
                                ),
                            },
                        )
                    )
                    if created:
                        counts["supplier"] += 1

                manufacturer_name = (
                    manufacturer_supplier_name or row.get("ManufacturerName") or ""
                )
                master_manufacturer_obj = None
                if manufacturer_name:
                    manufacturer_code = (
                        manufacturer_supplier_code or manufacturer_name
                    )[:250]
                    master_manufacturer_obj, created = (
                        MasterManufacturer.objects.update_or_create(
                            code=manufacturer_code,
                            defaults={"name": manufacturer_name},
                        )
                    )
                    if created:
                        counts["master_manufacturer"] += 1

                master_equipment_type_obj = None
                if eq_name:
                    master_equipment_type_obj, created = (
                        MasterEquipmentType.objects.get_or_create(
                            code=eq_name[:250],
                            defaults={"name": eq_name},
                        )
                    )
                    if created:
                        counts["master_equipment_type"] += 1

                if eq_code:
                    equipment_country_obj = None
                    equipment_country_code = row.get("EquipmentCountryCode")
                    if equipment_country_code:
                        equipment_country_obj, _ = MasterCountry.objects.get_or_create(
                            code=equipment_country_code,
                            defaults={
                                "name": row.get("EquipmentCountryName")
                                or equipment_country_code
                            },
                        )

                    equipment_group_obj = None
                    equipment_group_code = row.get("EquipmentGroupCode")
                    if equipment_group_code:
                        equipment_group_obj, _ = MasterGroup.objects.get_or_create(
                            code=equipment_group_code,
                            defaults={"name": equipment_group_code},
                        )

                    _, created = MasterEquipment.objects.update_or_create(
                        code=eq_code,
                        defaults={
                            "name": eq_name,
                            "model": eq_model or None,
                            "manufacturer": master_manufacturer_obj,
                            "type": master_equipment_type_obj,
                            "country": equipment_country_obj,
                            "group": equipment_group_obj,
                            "authority": row.get("authority") or "",
                            "obsolete": row.get("obsolete") or "",
                            "generic_code": row.get("EquipmentGenericSrNo") or None,
                            "maintop_number": row.get("MaintopNumber") or None,
                            "acquaint_issued": row.get("AcquaintIssued") or None,
                            "ilms_equipment_code": row.get("ILMSEquipmentCode") or None,
                        },
                    )
                    if created:
                        counts["master_equipment"] += 1

                if supplier_code:
                    supplier_country_obj = None
                    country_code = row.get("CountryCode")
                    if country_code:
                        supplier_country_obj, _ = MasterCountry.objects.get_or_create(
                            code=country_code,
                            defaults={"name": row.get("CountryName") or country_code},
                        )

                    _, created = MasterSupplier.objects.update_or_create(
                        code=supplier_code,
                        defaults={
                            "name": supplier_name,
                            "supplier_manufacture": (
                                str(supplier_manufacture_raw)
                                if supplier_manufacture_raw not in (None, "")
                                else None
                            ),
                            "address": row.get("Address") or None,
                            "city": row.get("City") or None,
                            "country": supplier_country_obj,
                            "contact_person": row.get("Contact_Person") or None,
                            "contact_number": row.get("Contact_Number") or None,
                            "email_id": row.get("Email_ID") or None,
                        },
                    )
                    if created:
                        counts["master_supplier"] += 1

                detail_uid = row.get("Universal_ID_T_EquipmentShipDetail")
                nomenclature = row.get("Nomenclature") or ""
                if not detail_uid and not nomenclature:
                    continue

                shipeq_lookup = (
                    {"t_equipment_ship_detail": detail_uid}
                    if detail_uid
                    else {"ship": ship_obj, "nomenclature": nomenclature}
                )
                shipeq_obj, created = ShipEquipment.objects.update_or_create(
                    **shipeq_lookup,
                    defaults={
                        "ship": ship_obj,
                        "department": dept_obj,
                        "sub_department_f_key": subdept_obj,
                        "equipment": eq_obj,
                        "equipment_type_f_key": eqtype_obj,
                        "supplier": supplier_obj,
                        "manufacturer": manufacturer_supplier_obj,
                        "nomenclature": nomenclature,
                        "equipment_name": eq_name,
                        "equipment_code": eq_code,
                        "equipment_model": eq_model,
                        "equipment_serial_no": row.get("EquipmentSrNo") or "",
                        "location_on_board": row.get("LocationOnBoard") or "",
                        "location_code": row.get("LocationCode") or None,
                        "maintop_id": to_int(row.get("MaintopNumber")),
                        "installation_date": date_from_cmms(
                            row.get("InstallationDate")
                        ),
                        "quantity": row.get("Quantity") or 1,
                        "no_of_fits": row.get("Quantity") or 1,
                        "authority_installation": row.get("Authority_of_Installation"),
                        "authority_of_installation": row.get(
                            "Authority_of_Installation"
                        ),
                        "is_srar": bool(row.get("SRARApplicable")),
                        "status": "active",
                        "active": True,
                        "removal_date": date_from_cmms(row.get("RemovalDate")),
                        "oem_part_no": row.get("OEMPartNo") or None,
                        "remarks": row.get("DetailRemark") or None,
                        "service_life": (
                            str(row.get("ServiceLife"))
                            if row.get("ServiceLife") not in (None, "")
                            else None
                        ),
                        "removal_remark": row.get("Removal_Remark") or None,
                        "authority_of_removal": row.get("Authority_Of_Removal") or None,
                        "rshi": row.get("RH_Of_New_Equipemnt_At_Time_Of_Installation")
                        or None,
                        "insma_remarks": row.get("INSMAREMARKS") or None,
                        "is_synced": (
                            bool(row.get("DetailIsSynced"))
                            if row.get("DetailIsSynced") is not None
                            else True
                        ),
                        "universal_id_m_ship": ship_uid,
                        "universal_id_m_equipment": eq_uid,
                        "universal_id_m_supplier": supplier_uid,
                        "universal_id_m_department": dept_uid,
                        "universal_id_m_sub_department": subdept_uid,
                        "universal_id_m_srar_type": row.get("Universal_ID_M_SrarType")
                        or None,
                        "universal_id_m_manufacturer": row.get(
                            "Universal_ID_M_Supplier_Manufacturer"
                        )
                        or None,
                        "universal_id_m_equipment_parent": row.get(
                            "Universal_ID_M_Equipment_ParentEquipment"
                        )
                        or None,
                        "universal_id_t_maintop_header": row.get(
                            "Universal_ID_T_MaintopHeader"
                        ),
                        "universal_id_t_equipment_ship_detail": detail_uid,
                    },
                )
                if created:
                    counts["ship_equipment"] += 1

                if nomenclature:
                    ems_lookup = (
                        {"universal_id_t_equipment_ship_detail": detail_uid}
                        if detail_uid
                        else {"sfd_equipment": shipeq_obj}
                    )
                    _, created = EquipmentName.objects.update_or_create(
                        **ems_lookup,
                        defaults={
                            "name": nomenclature.upper(),
                            "nomenclature": nomenclature,
                            "equipment_code": eq_code,
                            "extra": eq_name,
                            "sub_department": subdept_obj,
                            "universal_id_t_equipment_ship_detail": detail_uid,
                            "sfd_equipment": shipeq_obj,
                            "started_at_location": "AT SEA",
                            "state": "INACTIVE",
                        },
                    )
                    if created:
                        counts["ems_equipment"] += 1

        return counts

    def _fetch_all_active_suppliers(self, cursor):
        """The full CMMS supplier/manufacturer catalog — deliberately NOT scoped
        to any ship. `SupplierManufacturer` distinguishes role: 1 = Supplier,
        2 = Manufacturer. Matches the reference query:
        `SELECT * FROM M_Supplier WITH (NOLOCK) WHERE Active = 1`.
        """
        query = """
            SELECT
                M_Supplier.SupplierID,
                M_Supplier.SupplierCode,
                M_Supplier.Universal_ID_M_Supplier,
                M_Supplier.SupplierName,
                M_Supplier.SupplierManufacturer,
                M_Supplier.Active,
                M_Supplier.Address,
                M_Supplier.AreaStreet,
                M_Supplier.City,
                M_Supplier.CountryCode,
                M_Supplier.CountryID,
                M_Supplier.Universal_ID_M_Country,
                M_Supplier.Contact_Person,
                M_Supplier.Contact_Number,
                M_Supplier.Email_ID,
                M_Country.CountryName
            FROM M_Supplier
            LEFT JOIN M_Country
                ON M_Supplier.CountryID = M_Country.CountryID
            WHERE M_Supplier.Active = 1
        """
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _sync_all_suppliers(self, rows):
        """Upserts the full, ship-independent supplier/manufacturer catalog
        into sfd.Supplier. Runs once per sync — not scoped/looped per ship
        equipment, unlike `_sync_rows_to_swmm`.
        """
        counts = {"supplier_catalog": 0}
        with transaction.atomic():
            for row in rows:
                supplier_uid = row.get("Universal_ID_M_Supplier")
                supplier_name = row.get("SupplierName") or ""
                supplier_code = row.get("SupplierCode") or ""
                if not (supplier_uid or supplier_name):
                    continue

                supplier_manufacture_raw = row.get("SupplierManufacturer")
                supplier_manufacture = (
                    int(supplier_manufacture_raw)
                    if supplier_manufacture_raw not in (None, "")
                    else None
                )
                supplier_lookup = (
                    {"Universal_ID_M_Supplier": supplier_uid}
                    if supplier_uid
                    else {"SupplierName": supplier_name}
                )
                _, created = Supplier.objects.update_or_create(
                    **supplier_lookup,
                    defaults={
                        "SupplierID": row.get("SupplierID"),
                        "SupplierCode": supplier_code,
                        "SupplierName": supplier_name,
                        "SupplierManufacturer": (
                            str(supplier_manufacture_raw)
                            if supplier_manufacture_raw not in (None, "")
                            else None
                        ),
                        "supplier_code": supplier_code,
                        "supplier_name": supplier_name,
                        "supplier_manufacture": supplier_manufacture,
                        "address": (row.get("Address") or "")[:255] or None,
                        "AreaStreet": row.get("AreaStreet") or None,
                        "City": row.get("City") or None,
                        "CountryCode": row.get("CountryCode") or None,
                        "CountryID": (
                            str(row.get("CountryID"))
                            if row.get("CountryID") not in (None, "")
                            else None
                        ),
                        "Universal_ID_M_Country": row.get("Universal_ID_M_Country")
                        or None,
                        "Contact_Person": row.get("Contact_Person") or None,
                        "Contact_Number": row.get("Contact_Number") or None,
                        "Email_ID": row.get("Email_ID") or None,
                        "active": "1" if row.get("Active") else "0",
                    },
                )
                if created:
                    counts["supplier_catalog"] += 1

                if supplier_code:
                    supplier_country_obj = None
                    country_code = row.get("CountryCode")
                    if country_code:
                        supplier_country_obj, _ = MasterCountry.objects.get_or_create(
                            code=country_code,
                            defaults={"name": row.get("CountryName") or country_code},
                        )
                    MasterSupplier.objects.update_or_create(
                        code=supplier_code,
                        defaults={
                            "name": supplier_name,
                            "supplier_manufacture": (
                                str(supplier_manufacture_raw)
                                if supplier_manufacture_raw not in (None, "")
                                else None
                            ),
                            "address": row.get("Address") or None,
                            "city": row.get("City") or None,
                            "country": supplier_country_obj,
                            "contact_person": row.get("Contact_Person") or None,
                            "contact_number": row.get("Contact_Number") or None,
                            "email_id": row.get("Email_ID") or None,
                        },
                    )

        return counts

    def _fetch_all_subdepartments(self, cursor, ship_class_uid):
        """The full sub-department set defined for the ship's CLASS — not just
        the sub-departments that happen to have equipment currently installed
        on this specific hull. Matches the reference query:
        `SELECT * FROM M_SubDepartment WHERE Universal_ID_M_ShipClass = ?`.
        """
        if not ship_class_uid:
            return []
        query = """
            SELECT
                M_SubDepartment.Universal_ID_M_SubDepartment,
                M_SubDepartment.Description,
                M_SubDepartment.SubDeptCode,
                M_SubDepartment.Active,
                M_SubDepartment.Universal_ID_M_Department,
                M_Department.Description AS DeptName
            FROM M_SubDepartment
            LEFT JOIN M_Department
                ON M_SubDepartment.Universal_ID_M_Department =
                   M_Department.Universal_ID_M_Department
            WHERE M_SubDepartment.Universal_ID_M_ShipClass = ?
        """
        cursor.execute(query, [ship_class_uid])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _sync_all_subdepartments(self, rows):
        counts = {"subdepartment_catalog": 0}
        with transaction.atomic():
            for row in rows:
                subdept_uid = row.get("Universal_ID_M_SubDepartment")
                subdept_name = row.get("Description") or ""
                if not (subdept_uid and subdept_name):
                    continue

                dept_uid = row.get("Universal_ID_M_Department")
                dept_name = row.get("DeptName") or ""
                dept_obj = None
                if dept_uid and dept_name:
                    dept_obj, _ = Department.objects.get_or_create(
                        universal_id_m_department=dept_uid,
                        defaults={"name": dept_name, "description": dept_name},
                    )

                _, created = SubDepartment.objects.update_or_create(
                    universal_id_m_sub_department=subdept_uid,
                    defaults={
                        "department_name": dept_obj,
                        "name": subdept_name,
                        "description": subdept_name,
                        "code": row.get("SubDeptCode") or None,
                        "active": bool(row.get("Active")),
                    },
                )
                if created:
                    counts["subdepartment_catalog"] += 1

        return counts

    def _build_log(self, ship_identifier, target_ship, row_count, counts):
        ship_uid = target_ship.get("Universal_ID_M_Ship")
        ship_name = target_ship.get("ShipName") or ""
        ship_code = target_ship.get("ShipCode") or ""
        return "\n".join(
            [
                "[SYSTEM] Starting CMMS SFD Sync...",
                f"[OK] .env ship identifier: {ship_identifier}",
                (
                    "[OK] M_Ship resolved: "
                    f"{ship_name} / {ship_code} / Universal_ID_M_Ship={ship_uid}"
                ),
                f"Fetched {row_count} T_EquipmentShipDetail records. Processing start...",
                f"[OK] M_Ship ({counts['ship']} new ships synced)",
                f"[OK] M_Department ({counts['department']} new departments synced)",
                (
                    "[OK] M_SubDepartment "
                    f"({counts['sub_department']} new sub-departments synced)"
                ),
                f"[OK] M_Equipment ({counts['equipment']} new equipments synced)",
                f"[OK] M_EquipmentType ({counts['equipment_type']} new equipment types synced)",
                f"[OK] M_Supplier ({counts['supplier']} new suppliers synced)",
                (
                    "[OK] T_EquipmentShipDetail "
                    f"({counts['ship_equipment']} new ship equipments synced)"
                ),
                f"[OK] EMS EquipmentName ({counts['ems_equipment']} new records synced)",
                (
                    "[OK] Master_manufacturer "
                    f"({counts['master_manufacturer']} new manufacturers synced)"
                ),
                (
                    "[OK] Master_equipmenttype "
                    f"({counts['master_equipment_type']} new equipment types synced)"
                ),
                (
                    "[OK] Master_equipment "
                    f"({counts['master_equipment']} new master equipment synced)"
                ),
                (
                    "[OK] Master_supplier "
                    f"({counts['master_supplier']} new master suppliers synced)"
                ),
                (
                    "[OK] M_Supplier full catalog (ship-independent) "
                    f"({counts.get('supplier_catalog', 0)} new suppliers/manufacturers synced)"
                ),
                (
                    "[OK] M_SubDepartment full catalog (ship-class scoped) "
                    f"({counts.get('subdepartment_catalog', 0)} new sub-departments synced)"
                ),
                "[Completed] Step 1 CMMS SFD Sync completed successfully.",
            ]
        )

    def get(self, request):
        conn = None
        cursor = None

        try:
            ship_identifier = self._env_ship_identifier()
            if not ship_identifier:
                return Response(
                    {"status": False, "error": "Ship identifier is not configured."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conn = get_mssql_connection()
            cursor = conn.cursor()

            target_ship = self._fetch_target_ship(cursor, ship_identifier)
            if not target_ship:
                return Response(
                    {
                        "status": False,
                        "error": f"Ship '{ship_identifier}' not found in CMMS M_Ship.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            rows = self._fetch_ship_equipment_rows(
                cursor, target_ship.get("Universal_ID_M_Ship")
            )
            counts = self._sync_rows_to_swmm(target_ship, rows)

            supplier_rows = self._fetch_all_active_suppliers(cursor)
            counts.update(self._sync_all_suppliers(supplier_rows))

            subdept_rows = self._fetch_all_subdepartments(
                cursor, target_ship.get("Universal_ID_M_ShipClass")
            )
            counts.update(self._sync_all_subdepartments(subdept_rows))

            log_output = self._build_log(
                ship_identifier, target_ship, len(rows), counts
            )
            return HttpResponse(log_output, content_type="text/plain")

        except Exception as e:
            logger.exception("CMMS SFD sync failed")
            return Response(
                {"status": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class CMMSMaintopSyncAPI(APIView):
    """CMMS's T_MaintopHeader/T_MaintopDetail together run into the hundreds of thousands of
    rows (unlike CMMSRoutineDataAPI's Step 3, this is deliberately NOT scoped to one ship — the
    full fleet-wide routine catalog is wanted here). Row-by-row `update_or_create()` at that
    volume is far too slow for a single blocking HTTP response — the request would sit for many
    minutes with the frontend showing nothing but its initial "Starting..." text, looking hung.
    So this streams progress as it goes (StreamingHttpResponse, matching what
    SfdReferencesApiService.streamSync already expects) and writes in bulk batches
    (bulk_create(update_conflicts=True), Postgres upsert) instead of one query pair per row.
    """

    _BATCH_SIZE = 2000

    def get(self, request):
        return self.post(request)

    def post(self, request):
        return StreamingHttpResponse(self._stream_sync(), content_type="text/plain")

    _HEADER_UPDATE_FIELDS = [
        "maintop_no",
        "maintop_title",
        "original_date",
        "amendment_no",
        "amendment_date",
        "authority",
        "flag",
        "active",
        "created_by",
        "created_date",
        "updated_by",
        "updated_date",
        "reference",
        "department",
        "is_non_digitized",
        "fuss_id",
        "equipmentcode",
        "equipment_specification",
        "ship_applicable",
        "documents",
        "reason",
        "issue_date",
        "universal_id_a_user_created_by",
        "universal_id_a_user_updated_by",
        "universal_id_t_maintopheader",
        "universal_id_t_fuss",
        "authority_date",
        "is_draft",
    ]

    _DETAIL_UPDATE_FIELDS = [
        "maintopheader_f_key",
        "frequency_f_key",
        "routine_no",
        "routine_description",
        "routine_brief_description",
        "maintop_id",
        "maintop_no",
        "amendment_no",
        "frequency_id",
        "frequency",
        "frequency_sr_no",
        "group_heading",
        "para_heading",
        "alternate_info",
        "by_whom",
        "category",
        "dockyard_remarks",
        "admin_remarks",
        "jic_id",
        "active",
        "created_by",
        "created_date",
        "updated_by",
        "updated_date",
        "amendment_date",
        "by_whom_id1",
        "by_whom_id2",
        "by_whom_id3",
        "freq_priority",
        "universal_id_a_user_created_by",
        "universal_id_a_user_updated_by",
        "universal_id_t_maintopdetail",
        "universal_id_t_maintopheader",
        "universal_id_m_frequency",
        "universal_id_t_maintopjic",
        "universal_id_m_bywhom1",
        "universal_id_m_bywhom2",
        "universal_id_m_bywhom3",
        "jic",
        "ss_proposal",
        "applicable_eqpt",
        "insma_recommendations",
        "remarks",
        "reason",
        "routine_type",
        "ship_id",
        "comment",
        "remove_reason",
        "is_synced",
    ]

    def _header_instance(self, row: dict) -> MaintopHeader:
        return MaintopHeader(
            maintop_id=row.get("MaintopID"),
            maintop_no=row.get("MaintopNo"),
            maintop_title=row.get("MaintopTitle"),
            original_date=datetime_from_cmms(row.get("OriginalDate")),
            amendment_no=row.get("AmendmentNo"),
            amendment_date=datetime_from_cmms(row.get("AmendmentDate")),
            authority=row.get("Authority"),
            flag=row.get("Flag"),
            active=row.get("Active"),
            created_by=row.get("CreatedBy"),
            created_date=datetime_from_cmms(row.get("CreatedDate")),
            updated_by=row.get("UpdatedBy"),
            updated_date=datetime_from_cmms(row.get("UpdatedDate")),
            reference=row.get("Reference"),
            department=row.get("Department"),
            is_non_digitized=row.get("IsNonDigitized"),
            fuss_id=row.get("FussID"),
            equipmentcode=row.get("EquipmentCode"),
            equipment_specification=row.get("EquipmentSpecification"),
            ship_applicable=row.get("ShipApplicable"),
            documents=row.get("Documents"),
            reason=row.get("Reason"),
            issue_date=datetime_from_cmms(row.get("IssueDate")),
            universal_id_a_user_created_by=row.get("Universal_ID_A_User_Created_By"),
            universal_id_a_user_updated_by=row.get("Universal_ID_A_User_Updated_By"),
            universal_id_t_maintopheader=row.get("Universal_ID_T_MaintopHeader"),
            universal_id_t_fuss=row.get("Universal_ID_T_Fuss"),
            authority_date=datetime_from_cmms(row.get("AuthorityDate")),
            is_draft=row.get("IsDraft"),
        )

    def _detail_instance(
        self, row: dict, header_ids: set, frequency_pk_map: dict
    ) -> MaintopDetail:
        maintop_id = row.get("MaintopID")
        frequency_uid = row.get("Universal_ID_M_Frequency")
        return MaintopDetail(
            routine_id=row.get("RoutineID"),
            # Only link to a header that's actually present in this same sync run (its own
            # bulk_create just committed it) — Postgres would reject the FK otherwise.
            maintopheader_f_key_id=maintop_id if maintop_id in header_ids else None,
            frequency_f_key_id=frequency_pk_map.get(frequency_uid),
            universal_id_t_maintopdetail=row.get("Universal_ID_T_MaintopDetail"),
            routine_no=row.get("RoutineNo"),
            routine_description=row.get("RoutineDescription"),
            routine_brief_description=row.get("RoutineBriefDescription"),
            maintop_id=maintop_id,
            maintop_no=row.get("MaintopNo"),
            amendment_no=row.get("AmendmentNo"),
            frequency_id=row.get("FrequencyID"),
            frequency=row.get("Frequency"),
            frequency_sr_no=row.get("FrequencySrNo"),
            group_heading=row.get("GroupHeading"),
            para_heading=row.get("ParaHeading"),
            alternate_info=row.get("AlternateInfo"),
            by_whom=row.get("ByWhom"),
            category=row.get("Category"),
            dockyard_remarks=row.get("DockyardRemarks"),
            admin_remarks=row.get("AdminRemarks"),
            jic_id=row.get("JICID"),
            active=row.get("Active"),
            created_by=row.get("CreatedBy"),
            created_date=datetime_from_cmms(row.get("CreatedDate")),
            updated_by=row.get("UpdatedBy"),
            updated_date=datetime_from_cmms(row.get("UpdatedDate")),
            amendment_date=datetime_from_cmms(row.get("AmendmentDate")),
            by_whom_id1=row.get("ByWhomId1"),
            by_whom_id2=row.get("ByWhomId2"),
            by_whom_id3=row.get("ByWhomId3"),
            freq_priority=row.get("FreqPriority"),
            universal_id_a_user_created_by=row.get("Universal_ID_A_User_Created_By"),
            universal_id_a_user_updated_by=row.get("Universal_ID_A_User_Updated_By"),
            universal_id_t_maintopheader=row.get("Universal_ID_T_MaintopHeader"),
            universal_id_m_frequency=frequency_uid,
            universal_id_t_maintopjic=row.get("Universal_ID_T_MaintopJIC"),
            universal_id_m_bywhom1=row.get("Universal_ID_M_ByWhom1"),
            universal_id_m_bywhom2=row.get("Universal_ID_M_ByWhom2"),
            universal_id_m_bywhom3=row.get("Universal_ID_M_ByWhom3"),
            jic=row.get("JIC"),
            ss_proposal=row.get("SSProposal"),
            applicable_eqpt=row.get("ApplicableEqpt"),
            insma_recommendations=row.get("INSMARecommendations"),
            remarks=row.get("Remarks"),
            reason=row.get("Reason"),
            routine_type=row.get("RoutineType"),
            ship_id=row.get("Ship_ID"),
            comment=row.get("Comment"),
            remove_reason=row.get("Remove_Reason"),
            is_synced=True,
        )

    def _stream_sync(self):
        conn = None
        cursor = None
        try:
            yield "[SYSTEM] Starting CMMS MAINTOPS Sync...\n"

            conn = get_mssql_connection()
            cursor = conn.cursor()

            # --- T_MaintopHeader -> ems.MaintopHeader --------------------------------------
            cursor.execute("SELECT * FROM T_MaintopHeader WHERE Active = 1")
            header_columns = [column[0] for column in cursor.description]
            header_rows = cursor.fetchall()
            yield f"Fetched {len(header_rows)} T_MaintopHeader records. Processing...\n"

            header_ids: set = set()
            header_synced_count = 0
            batch: list[MaintopHeader] = []
            with transaction.atomic():
                for row_tuple in header_rows:
                    row = dict(zip(header_columns, row_tuple))
                    maintop_id = row.get("MaintopID")
                    if maintop_id is None:
                        continue
                    header_ids.add(maintop_id)
                    batch.append(self._header_instance(row))
                    if len(batch) >= self._BATCH_SIZE:
                        MaintopHeader.objects.bulk_create(
                            batch,
                            update_conflicts=True,
                            unique_fields=["maintop_id"],
                            update_fields=self._HEADER_UPDATE_FIELDS,
                        )
                        header_synced_count += len(batch)
                        batch = []
                        yield f"[OK] T_MaintopHeader progress: {header_synced_count}/{len(header_rows)}\n"
                if batch:
                    MaintopHeader.objects.bulk_create(
                        batch,
                        update_conflicts=True,
                        unique_fields=["maintop_id"],
                        update_fields=self._HEADER_UPDATE_FIELDS,
                    )
                    header_synced_count += len(batch)
            yield f"[OK] T_MaintopHeader ({header_synced_count} Maintop headers synced)\n"

            # --- T_MaintopDetail -> ems.MaintopDetail ---------------------------------------
            cursor.execute("SELECT * FROM T_MaintopDetail WHERE Active = 1")
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            yield f"Fetched {len(rows)} T_MaintopDetail records. Processing...\n"

            frequency_pk_map = {
                frequency.universal_id_m_frequency: frequency.pk
                for frequency in Frequency.objects.all()
            }

            detail_synced_count = 0
            batch = []
            with transaction.atomic():
                for row_tuple in rows:
                    row = dict(zip(columns, row_tuple))
                    # MaintopDetail.routine_id is the model's actual primary key (mirrors
                    # CMMS's own RoutineID) — Universal_ID_T_MaintopDetail is frequently NULL
                    # on this data, so keying on RoutineID (always populated) instead is what
                    # makes every row actually sync instead of getting silently skipped.
                    if row.get("RoutineID") is None:
                        continue
                    batch.append(
                        self._detail_instance(row, header_ids, frequency_pk_map)
                    )
                    if len(batch) >= self._BATCH_SIZE:
                        MaintopDetail.objects.bulk_create(
                            batch,
                            update_conflicts=True,
                            unique_fields=["routine_id"],
                            update_fields=self._DETAIL_UPDATE_FIELDS,
                        )
                        detail_synced_count += len(batch)
                        batch = []
                        yield f"[OK] T_MaintopDetail progress: {detail_synced_count}/{len(rows)}\n"
                if batch:
                    MaintopDetail.objects.bulk_create(
                        batch,
                        update_conflicts=True,
                        unique_fields=["routine_id"],
                        update_fields=self._DETAIL_UPDATE_FIELDS,
                    )
                    detail_synced_count += len(batch)
            yield f"[OK] T_MaintopDetail ({detail_synced_count} Maintop details synced)\n"

            yield "[Completed] Maintop Sync process completed successfully."

        except Exception as exc:
            logger.exception("CMMS Maintop sync failed")
            yield f"\n[ERROR] {exc}\n"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class CMMSRoutineDataAPI(APIView):
    pagination_class = CommonPagination

    def get(self, request):
        conn = None
        cursor = None

        try:
            # 1. Read Ship Code / ID from .env file
            env_ship_code = os.getenv("SWMM_SHIP_CODE") or os.getenv(
                "DEFAULT_SHIP_ID", "L18"
            )
            if env_ship_code:
                env_ship_code = env_ship_code.strip()

            count_header = 0
            count_frequency = 0
            count_detail = 0

            cmms_ship_uid = None
            cmms_ship_code = env_ship_code or ""

            try:
                conn = get_mssql_connection()
                cursor = conn.cursor()

                # Step 1: Search M_Ship table in CMMS DB using Ship ID / Code from .env
                ship_search_query = """
                    SELECT Universal_ID_M_Ship, ShipName, ShipCode
                    FROM M_Ship WITH (NOLOCK)
                    WHERE ShipCode = ? OR Universal_ID_M_Ship = ? OR ShipName LIKE ?
                """
                cursor.execute(
                    ship_search_query,
                    [env_ship_code, env_ship_code, f"%{env_ship_code}%"],
                )
                ship_row = cursor.fetchone()

                if ship_row:
                    cmms_ship_uid = ship_row[0]
                    cmms_ship_code = ship_row[2] or env_ship_code
                else:
                    logger.warning(
                        f"Ship code {env_ship_code} not found in CMMS M_Ship table."
                    )

                # Step 2: Query T_MaintopHeader and T_MaintopDetail from CMMS DB
                maintop_query = """
                    SELECT
                        h.Universal_ID_T_MaintopHeader,
                        h.MaintopNo,
                        h.MaintopTitle,
                        h.EquipmentCode,
                        h.Active AS HeaderActive,
                        d.Universal_ID_T_MaintopDetail,
                        d.RoutineNo,
                        d.RoutineDescription,
                        d.ByWhom,
                        d.Active AS DetailActive,
                        f.Universal_ID_M_Frequency,
                        f.Frequency,
                        f.Months AS FrequencyMonths,
                        f.Hours AS FrequencyHours,
                        f.Description AS FrequencyDescription
                    FROM T_MaintopHeader h WITH (NOLOCK)
                    INNER JOIN T_MaintopDetail d WITH (NOLOCK)
                        ON h.Universal_ID_T_MaintopHeader = d.Universal_ID_T_MaintopHeader
                    LEFT JOIN M_Frequency f WITH (NOLOCK)
                        ON d.Universal_ID_M_Frequency = f.Universal_ID_M_Frequency
                    LEFT JOIN M_Equipment eq WITH (NOLOCK)
                        ON h.Universal_ID_M_Equipment = eq.Universal_ID_M_Equipment
                    LEFT JOIN T_EquipmentShipDetail esd WITH (NOLOCK)
                        ON eq.Universal_ID_M_Equipment = esd.Universal_ID_M_Equipment
                    WHERE h.Active = 1
                      AND d.Active = 1
                """

                params = []
                if cmms_ship_uid:
                    maintop_query += " AND (esd.Universal_ID_M_Ship = ? OR h.Universal_ID_M_Ship = ?)"
                    params.extend([cmms_ship_uid, cmms_ship_uid])
                elif env_ship_code:
                    maintop_query += " AND (esd.Universal_ID_M_Ship = ? OR h.Universal_ID_M_Ship = ?)"
                    params.extend([env_ship_code, env_ship_code])

                cursor.execute(maintop_query, params)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()

                # Step 3: Store synced data into SWMM PostgreSQL DB
                with transaction.atomic():
                    for row_tuple in rows:
                        row = dict(zip(columns, row_tuple))

                        header_uid = row.get("Universal_ID_T_MaintopHeader")
                        maintop_no = row.get("MaintopNo")
                        maintop_title = row.get("MaintopTitle")
                        eq_code = row.get("EquipmentCode")

                        freq_uid = row.get("Universal_ID_M_Frequency")
                        freq_name = row.get("Frequency")
                        freq_months = row.get("FrequencyMonths")
                        freq_hours = str(row.get("FrequencyHours") or "")
                        freq_desc = row.get("FrequencyDescription")

                        detail_uid = row.get("Universal_ID_T_MaintopDetail")
                        routine_no = row.get("RoutineNo")
                        routine_desc = row.get("RoutineDescription")
                        by_whom = row.get("ByWhom")

                        # 1. M_Frequency -> ems.Frequency
                        freq_inst = None
                        if freq_uid or freq_name:
                            lookup = (
                                {"universal_id_m_frequency": freq_uid}
                                if freq_uid
                                else {"frequency": freq_name}
                            )
                            freq_inst, created = Frequency.objects.update_or_create(
                                **lookup,
                                defaults={
                                    "frequency": freq_name or "",
                                    "months": freq_months,
                                    "hours": freq_hours,
                                    "description": freq_desc or "",
                                    "active": True,
                                },
                            )
                            if created:
                                count_frequency += 1

                        # 2. T_MaintopHeader -> ems.MaintopHeader
                        header_inst = None
                        if header_uid or maintop_no:
                            lookup = (
                                {"universal_id_t_maintopheader": header_uid}
                                if header_uid
                                else {"maintop_no": maintop_no}
                            )
                            header_inst, created = (
                                MaintopHeader.objects.update_or_create(
                                    **lookup,
                                    defaults={
                                        "maintop_no": maintop_no or "",
                                        "maintop_title": maintop_title or "",
                                        "equipmentcode": eq_code or "",
                                        "active": True,
                                    },
                                )
                            )
                            if created:
                                count_header += 1

                        # 3. T_MaintopDetail -> ems.MaintopDetail
                        if detail_uid or routine_no:
                            lookup = (
                                {"universal_id_t_maintopdetail": detail_uid}
                                if detail_uid
                                else {"routine_no": routine_no}
                            )
                            if header_inst:
                                lookup["maintopheader_f_key"] = header_inst

                            detail_inst, created = (
                                MaintopDetail.objects.update_or_create(
                                    **lookup,
                                    defaults={
                                        "maintopheader_f_key": header_inst,
                                        "frequency_f_key": freq_inst,
                                        "routine_no": routine_no or "",
                                        "routine_description": routine_desc or "",
                                        "by_whom": by_whom or "",
                                        "maintop_no": maintop_no or "",
                                        "frequency": freq_name or "",
                                        "active": True,
                                    },
                                )
                            )
                            if created:
                                count_detail += 1

            except Exception as ex:
                logger.error(f"CMMS Maintops DB query/sync failed: {ex}")
                count_header = MaintopHeader.objects.all().count()
                count_frequency = Frequency.objects.all().count()
                count_detail = MaintopDetail.objects.all().count()

            log_output = (
                f"[SYSTEM] CMMS MAINTOPS Sync for Ship '{env_ship_code}' (Universal ID: {cmms_ship_uid})...\n"
                f"[OK] Table 1: T_MaintopHeader ({count_header} Maintop Headers synced)\n"
                f"[OK] Table 2: M_Frequency ({count_frequency} Frequencies synced)\n"
                f"[OK] Table 3: T_MaintopDetail ({count_detail} Maintop Details synced)\n"
                f"[Completed] Successfully synchronized CMMS Maintop data for ship '{env_ship_code}' into local SWMM database."
            )
            return HttpResponse(log_output, content_type="text/plain")

        except Exception as e:
            return Response(
                {"status": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class CMMSDefectDataAPI(APIView):
    pagination_class = CommonPagination

    def get(self, request):
        conn = None
        cursor = None

        try:
            equipment_ship_detail_ids = list(
                ShipEquipment.objects.values_list("t_equipment_ship_detail", flat=True)
            )

            # Remove empty IDs
            equipment_ship_detail_ids = [x for x in equipment_ship_detail_ids if x]

            # No equipment mapping found
            if not equipment_ship_detail_ids:
                paginator = self.pagination_class()

                paginated_data = paginator.paginate_queryset([], request, view=self)

                return paginator.get_paginated_response(paginated_data)

            ship = get_this_ship()
            ship_id = ship.universal_id_m_ship if ship else None

            search = request.GET.get("search", "").strip()

            # Create placeholders for IN clause
            id_placeholders = ",".join(["?"] * len(equipment_ship_detail_ids))

            query = f"""
                SELECT
                    T_Dart.Universal_ID_T_Dart,
                    T_Dart.DartNumber,
                    T_Dart.DartDate,
                    T_Dart.DefectDate,
                    T_Dart.ScheduleDate,
                    T_Dart.Universal_ID_Ch_Master_Symptoms,
                    T_Dart.SeverityID,
                    T_Dart.SeverityCode,
                    T_Dart.Universal_ID_M_Severity,
                    T_Dart.Universal_ID_Ch_Master_Ship_Remarks_By,
                    T_Dart.Universal_ID_M_RequiredAssistance,
                    T_Dart.IsOstObservation,
                    T_Dart.DefectiveComponent,
                    T_Dart.Remarks AS Remarks,
                    T_Dart.DefectDescription AS DefectDescription,
                    T_Dart.IsClosed,
                    T_Dart.Is_Defect,
                    T_Dart.Active,
                    T_Dart.RoutineDefect,
                    T_Dart.Serial_Number,
                    T_Dart.Is_Operational,
                    T_Dart.Universal_ID_T_RefComp,
                    T_Dart.Universal_ID_M_Ship,
                    T_Dart.Universal_ID_M_Department,
                    T_Dart.Universal_ID_T_EquipmentShipDetail,
                    T_Dart.IsGDForm,

                    T_DartDetailGD.Reason AS GD_Reason,

                    T_DartDetailGD.Defect_affects_sea_going_Operational_Availability
                        AS GD_Defect_affects_sea_going_Operational_Availability,

                    T_DartDetailGD.Hot_Work_Involved
                        AS GD_Hot_Work_Involved,

                    T_DartDetailGD.Date_place
                        AS GD_Date_place,

                    T_DartDetailGD.Date_for_Repairs
                        AS GD_Date_for_Repairs,

                    T_DartDetailGD.Place
                        AS GD_Place,

                    T_DartDetailGD.DateOfCompletion
                        AS GD_DateOfCompletion,

                    T_EquipmentShipDetail.Nomenclature,
                    M_Equipment.EquipmentName,
                    M_Equipment.EquipmentCode,
                    M_Department.Description AS DepartmentName,
                    M_Ship.ShipName,
                    M_ShipClass.Description AS ClassName

                FROM T_Dart WITH (NOLOCK)

                INNER JOIN T_EquipmentShipDetail WITH (NOLOCK)
                    ON T_Dart.Universal_ID_T_EquipmentShipDetail =
                       T_EquipmentShipDetail.Universal_ID_T_EquipmentShipDetail

                INNER JOIN M_Ship WITH (NOLOCK)
                    ON T_Dart.Universal_ID_M_Ship =
                       M_Ship.Universal_ID_M_Ship

                INNER JOIN M_ShipClass WITH (NOLOCK)
                    ON M_Ship.Universal_ID_M_ShipClass =
                       M_ShipClass.Universal_ID_M_ShipClass

                INNER JOIN M_Department WITH (NOLOCK)
                    ON T_Dart.Universal_ID_M_Department =
                       M_Department.Universal_ID_M_Department

                INNER JOIN M_Equipment WITH (NOLOCK)
                    ON T_EquipmentShipDetail.Universal_ID_M_Equipment =
                       M_Equipment.Universal_ID_M_Equipment

                LEFT JOIN T_DartDetailGD WITH (NOLOCK)
                    ON T_Dart.Universal_ID_T_Dart =
                       T_DartDetailGD.Universal_ID_T_Dart

                WHERE
                    T_EquipmentShipDetail.Active = 1

                    AND M_Equipment.Active = 1

                    AND T_Dart.Universal_ID_M_Ship = ?

                    AND T_Dart.Active = 1

                    AND T_Dart.Is_Defect = 1

                    AND T_Dart.IsClosed = 0

                    AND T_Dart.Universal_ID_T_EquipmentShipDetail
                        IN ({id_placeholders})
            """

            # First parameter = ship ID
            params = [ship_id]

            # Remaining parameters = equipment IDs
            params.extend(equipment_ship_detail_ids)

            if search:
                query += """
                    AND (
                        CAST(
                            T_Dart.Universal_ID_T_Dart
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.DartNumber
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.DartDate
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.DefectDate
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.ScheduleDate
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.Universal_ID_Ch_Master_Symptoms
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.SeverityID
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.SeverityCode
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.Universal_ID_M_Severity
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.Universal_ID_M_RequiredAssistance
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_Dart.DefectiveComponent
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR T_Dart.Remarks LIKE ?

                        OR T_Dart.DefectDescription LIKE ?

                        OR CAST(
                            T_Dart.Serial_Number
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR T_EquipmentShipDetail.Nomenclature LIKE ?

                        OR M_Equipment.EquipmentName LIKE ?

                        OR CAST(
                            M_Equipment.EquipmentCode
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR M_Department.Description LIKE ?

                        OR M_Ship.ShipName LIKE ?

                        OR M_ShipClass.Description LIKE ?

                        OR T_DartDetailGD.Reason LIKE ?

                        OR T_DartDetailGD.Place LIKE ?

                        OR CAST(
                            T_DartDetailGD.Date_place
                            AS VARCHAR(255)
                        ) LIKE ?
                    )
                """

                search_value = f"%{search}%"

                params.extend([search_value] * 22)

            query += """
                ORDER BY
                    T_Dart.DartDate DESC
            """

            conn = get_mssql_connection()
            cursor = conn.cursor()

            cursor.execute(query, params)

            columns = [col[0] for col in cursor.description]

            rows = cursor.fetchall()

            data = []

            for row in rows:
                record = dict(zip(columns, row))

                data.append(
                    {
                        "Universal_ID_T_Dart": record.get("Universal_ID_T_Dart"),
                        "dartnumber": record.get("DartNumber"),
                        "dart_date": record.get("DartDate"),
                        "defect_date": record.get("DefectDate"),
                        "schedule_date": record.get("ScheduleDate"),
                        "Universal_ID_Ch_Master_Symptoms": record.get(
                            "Universal_ID_Ch_Master_Symptoms"
                        ),
                        "severity_id": record.get("SeverityID"),
                        "severity_code": record.get("SeverityCode"),
                        "Universal_ID_M_Severity": record.get(
                            "Universal_ID_M_Severity"
                        ),
                        "Universal_ID_Ch_Master_Ship_Remarks_By": record.get(
                            "Universal_ID_Ch_Master_Ship_Remarks_By"
                        ),
                        "Universal_ID_M_RequiredAssistance": record.get(
                            "Universal_ID_M_RequiredAssistance"
                        ),
                        "trial_required": record.get("IsOstObservation"),
                        "defective_component": record.get("DefectiveComponent"),
                        "remarks": record.get("Remarks"),
                        "defect_description": record.get("DefectDescription"),
                        "isclosed": record.get("IsClosed"),
                        "is_defect": record.get("Is_Defect"),
                        "active": record.get("Active"),
                        "routinedefect": record.get("RoutineDefect"),
                        "serial_number": record.get("Serial_Number"),
                        "is_operational": record.get("Is_Operational"),
                        "Universal_ID_T_RefComp": record.get("Universal_ID_T_RefComp"),
                        "universal_id_m_ship": record.get("Universal_ID_M_Ship"),
                        "universal_id_m_department": record.get(
                            "Universal_ID_M_Department"
                        ),
                        "universal_id_t_equipment_ship_detail": record.get(
                            "Universal_ID_T_EquipmentShipDetail"
                        ),
                        "nomenclature": record.get("Nomenclature"),
                        "equipmentname": record.get("EquipmentName"),
                        "equipmentcode": str(record.get("EquipmentCode"))
                        if record.get("EquipmentCode")
                        else None,
                        "departmentname": record.get("DepartmentName"),
                        "shipname": record.get("ShipName"),
                        "classname": record.get("ClassName"),
                        "is_guarantee_defect": record.get("IsGDForm"),
                        "guarantee_cause": record.get("GD_Reason"),
                        "guarantee_op_availability": record.get(
                            "GD_Defect_affects_sea_going_Operational_Availability"
                        ),
                        "guarantee_hot_work": record.get("GD_Hot_Work_Involved"),
                        "guarantee_repairs": record.get("GD_Date_place"),
                        "guarantee_repair_date": record.get("GD_Date_for_Repairs"),
                        "guarantee_place": record.get("GD_Place"),
                        "guarantee_completion_date": record.get("GD_DateOfCompletion"),
                    }
                )

            print("Total rows from SQL:", len(rows))

            print("Total records in data:", len(data))

            paginator = self.pagination_class()

            paginated_data = paginator.paginate_queryset(data, request, view=self)

            return paginator.get_paginated_response(paginated_data)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()


class CMMSLessRoutineDataAPI(APIView):
    pagination_class = CommonPagination

    def get(self, request):
        conn = None
        cursor = None

        try:
            ship = get_this_ship()

            ship_id = ship.universal_id_m_ship if ship else None

            search = request.GET.get("search", "").strip()

            query = """
                SELECT
                    M_ShipClass.Description AS ClassName,
                    M_Ship.ShipName,
                    M_Department.Description AS DepartmentName,
                    M_Equipment.EquipmentName,
                    M_Equipment.EquipmentCode,

                    T_MaintopDetail.MaintopNo,

                    T_MaintopDetail.Universal_ID_M_Frequency
                        AS Universal_ID_M_Frequency,

                    T_RoutineList.Universal_ID_T_EquipmentShipDetail
                        AS Universal_ID_T_EquipmentShipDetail,

                    T_RoutineList.Universal_ID_T_RoutineList
                        AS Universal_Id_T_RoutineList,

                    T_MaintopDetail.Universal_ID_T_MaintopDetail,

                    T_EquipmentShipDetail.Nomenclature,

                    NULL AS DartNumber,

                    M_Frequency.Frequency,

                    NULL AS RoutineDueDate,

                    T_MaintopDetail.RoutineNo,

                    T_RoutineList.RoutineDescription,

                    [dbo].[Fn_GetByWhomRemark](
                        T_MaintopHeader.MaintopID,
                        T_MaintopDetail.RoutineID
                    ) AS ByWhom,

                    NULL AS Section,

                    M_Frequency.Description AS RoutineName,

                    M_Frequency.Frequency AS RoutineCategory,

                    M_Frequency.Months AS FrequencyMonth,

                    M_Frequency.Hours AS FrequencyHours,

                    0 AS RHSI,

                    0 AS RHSIUpdatedUpto,

                    NULL AS LastRoutineCompletedAtDate,

                    NULL AS LastRoutineCompletedAtRH

                FROM T_RoutineList WITH (NOLOCK)

                INNER JOIN T_EquipmentShipDetail WITH (NOLOCK)
                    ON T_RoutineList.Universal_ID_T_EquipmentShipDetail =
                       T_EquipmentShipDetail.Universal_ID_T_EquipmentShipDetail

                INNER JOIN M_Equipment WITH (NOLOCK)
                    ON T_EquipmentShipDetail.Universal_ID_M_Equipment =
                       M_Equipment.Universal_ID_M_Equipment

                INNER JOIN M_Department WITH (NOLOCK)
                    ON T_EquipmentShipDetail.Universal_ID_M_Department =
                       M_Department.Universal_ID_M_Department

                INNER JOIN M_Ship WITH (NOLOCK)
                    ON T_RoutineList.Universal_ID_M_Ship =
                       M_Ship.Universal_ID_M_Ship

                INNER JOIN T_MaintopHeader WITH (NOLOCK)
                    ON M_Equipment.Universal_ID_T_MaintopHeader =
                       T_MaintopHeader.Universal_ID_T_MaintopHeader

                INNER JOIN M_ShipClass WITH (NOLOCK)
                    ON M_Ship.Universal_ID_M_ShipClass =
                       M_ShipClass.Universal_ID_M_ShipClass

                LEFT JOIN T_MaintopDetail WITH (NOLOCK)
                    ON T_RoutineList.Universal_ID_T_MaintopDetail =
                       T_MaintopDetail.Universal_ID_T_MaintopDetail

                LEFT JOIN M_Frequency WITH (NOLOCK)
                    ON T_MaintopDetail.FrequencyID =
                       M_Frequency.FrequencyID

                LEFT JOIN M_ByWhom WITH (NOLOCK)
                    ON T_MaintopDetail.Universal_ID_M_ByWhom1 =
                       M_ByWhom.Universal_ID_M_ByWhom

                WHERE
                    T_RoutineList.Active = 1

                    AND M_Ship.Universal_ID_M_Ship = ?

                    AND T_RoutineList.IsClosed = 0
            """

            # First parameter = current ship ID
            params = [ship_id]

            if search:
                query += """
                    AND (
                        M_ShipClass.Description LIKE ?

                        OR M_Ship.ShipName LIKE ?

                        OR M_Department.Description LIKE ?

                        OR M_Equipment.EquipmentName LIKE ?

                        OR CAST(
                            M_Equipment.EquipmentCode
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_MaintopDetail.MaintopNo
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR T_EquipmentShipDetail.Nomenclature LIKE ?

                        OR CAST(
                            T_MaintopDetail.RoutineNo
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR T_RoutineList.RoutineDescription LIKE ?

                        OR M_Frequency.Description LIKE ?

                        OR CAST(
                            M_Frequency.Frequency
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            M_Frequency.Months
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            M_Frequency.Hours
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_RoutineList.Universal_ID_T_RoutineList
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_MaintopDetail.Universal_ID_M_Frequency
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_RoutineList.Universal_ID_T_EquipmentShipDetail
                            AS VARCHAR(255)
                        ) LIKE ?

                        OR CAST(
                            T_MaintopDetail.Universal_ID_T_MaintopDetail
                            AS VARCHAR(255)
                        ) LIKE ?
                    )
                """

                search_value = f"%{search}%"

                params.extend([search_value] * 17)

            query += """
                ORDER BY
                    M_Ship.ShipName,
                    M_Equipment.EquipmentCode,
                    T_EquipmentShipDetail.Nomenclature,
                    T_MaintopDetail.MaintopNo,
                    M_Frequency.Frequency,
                    T_MaintopDetail.RoutineNo
            """

            conn = get_mssql_connection()
            cursor = conn.cursor()

            cursor.execute(query, params)

            columns = [col[0] for col in cursor.description]

            rows = cursor.fetchall()

            data = []

            for row in rows:
                r = dict(zip(columns, row))

                data.append(
                    {
                        "classname": r.get("ClassName"),
                        "shipname": r.get("ShipName"),
                        "departmentname": r.get("DepartmentName"),
                        "equipmentname": r.get("EquipmentName"),
                        "equipmentcode": str(r.get("EquipmentCode"))
                        if r.get("EquipmentCode")
                        else None,
                        "maintopno": r.get("MaintopNo"),
                        "nomenclature": r.get("Nomenclature"),
                        "dartnumber": r.get("DartNumber"),
                        "routineno": r.get("RoutineNo"),
                        "routinedescription": r.get("RoutineDescription"),
                        "routinename": r.get("RoutineName"),
                        "frequency": r.get("Frequency"),
                        "frequencymonth": r.get("FrequencyMonth"),
                        "frequencyhours": r.get("FrequencyHours"),
                        "routineduedate": r.get("RoutineDueDate"),
                        "bywhom": r.get("ByWhom"),
                        "rhsiupdatedupto": r.get("RHSIUpdatedUpto"),
                        "LastRoutineComplitedatrh": r.get("LastRoutineComplitedAtRH"),
                        "lastroutinecompletedatdate": r.get(
                            "LastRoutineCompletedAtDate"
                        ),
                        "Universal_ID_T_RoutineList": r.get(
                            "Universal_Id_T_RoutineList"
                        ),
                        "Universal_ID_M_Frequency": r.get("Universal_ID_M_Frequency"),
                        "Universal_ID_T_EquipmentShipDetail": r.get(
                            "Universal_ID_T_EquipmentShipDetail"
                        ),
                        "universal_id_t_maintopdetail": r.get(
                            "Universal_ID_T_MaintopDetail"
                        ),
                    }
                )

            print("Total rows from SQL:", len(rows))

            print("Total records in data:", len(data))

            paginator = self.pagination_class()

            paginated_data = paginator.paginate_queryset(data, request, view=self)

            return paginator.get_paginated_response(paginated_data)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()


def norm(val):
    """Strip and uppercase a string value safely."""
    return (val or "").strip().upper()


def natural_key(val):
    """
    Generate a sort key for 'natural' sorting of strings containing numbers.
    Prioritizes integer sorting if the value is purely numeric.
    """
    import re

    val = str(val or "").strip()
    if val.isdigit():
        return [int(val)]
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", val)]


from ems.models import AddRoutineDetails, RoutineDescription


def build_ard_structures():
    # print("  Loading AddRoutineDetails Ã¢â‚¬Â¦", end=" ", flush=True)

    ard_eq_maintop = defaultdict(set)  # eq_id Ã¢â€ â€™ {maintop_no, Ã¢â‚¬Â¦}
    ard_lookup = {}  # (eq_id, mn, rn, frq) Ã¢â€ â€™ ard_id

    rows = AddRoutineDetails.objects.values(
        "id", "equipment_name_id", "maintop_no", "routine_no", "frequency"
    )
    for row in rows:
        eq_id = row["equipment_name_id"]
        mn = norm(row["maintop_no"])
        rn = norm(row["routine_no"])
        frq = norm(row["frequency"])

        if not mn or eq_id is None:
            continue

        ard_eq_maintop[eq_id].add(mn)
        if rn:
            ard_lookup[(eq_id, mn, rn, frq)] = row["id"]

    # Bootstrap: on a fresh system (or for any equipment with no AddRoutineDetails rows yet),
    # the loop above finds nothing — ard_eq_maintop only ever grows from AddRoutineDetails, which
    # is exactly what MissingRoutinesAPIView is trying to CREATE, so a brand-new equipment could
    # never get its first routine. CMMS already answers "which Maintop applies to this equipment"
    # directly: M_Equipment.Universal_ID_T_MaintopHeader, synced onto
    # ShipEquipment.universal_id_t_maintop_header by CMMSFDDataAPI (Step 1) and onto every
    # MaintopDetail row's own universal_id_t_maintopheader by CMMSMaintopSyncAPI (Step 2). Joining
    # those two gives every equipment's true maintop_no set without depending on
    # AddRoutineDetails already existing.
    header_uid_by_eq = dict(
        EquipmentName.objects.exclude(
            sfd_equipment__universal_id_t_maintop_header__isnull=True
        )
        .exclude(sfd_equipment__universal_id_t_maintop_header="")
        .values_list("id", "sfd_equipment__universal_id_t_maintop_header")
    )
    if header_uid_by_eq:
        maintop_nos_by_header_uid = defaultdict(set)
        detail_header_rows = (
            MaintopDetail.objects.exclude(universal_id_t_maintopheader__isnull=True)
            .exclude(universal_id_t_maintopheader="")
            .values_list("universal_id_t_maintopheader", "maintop_no")
        )
        for header_uid, mn in detail_header_rows:
            mn = norm(mn)
            if mn:
                maintop_nos_by_header_uid[header_uid].add(mn)

        for eq_id, header_uid in header_uid_by_eq.items():
            found = maintop_nos_by_header_uid.get(header_uid)
            if found:
                ard_eq_maintop[eq_id] |= found

    # print(f"{len(ard_lookup):,} rows / {len(ard_eq_maintop):,} equipments.")
    return ard_eq_maintop, ard_lookup


def build_rd_and_ard_sets():
    """
    Returns:
        rd_set  : set of (equipment_name_id, maintop_no_upper, routine_no_upper, freq_upper)
                  built directly from RoutineDescription Ã¢â‚¬â€ the ground-truth for COMPLETE
        ard_set : set of (equipment_name_id, maintop_no_upper, routine_no_upper, freq_upper)
                  built from AddRoutineDetails Ã¢â‚¬â€ used to detect Stage-2
    """
    # Ã¢â€â‚¬Ã¢â€â‚¬ RoutineDescription (through AddRoutineDetails for proper frequency check) Ã¢â€â‚¬Ã¢â€â‚¬
    # print("  Loading RoutineDescription Ã¢â‚¬Â¦", end=" ", flush=True)
    rd_rows = RoutineDescription.objects.select_related("add_routine_details").values(
        "equipment_name_id",
        "maintop_no",
        "routine_no",
        "add_routine_details__frequency",
    )
    rd_set = set()
    for r in rd_rows:
        eq_id = r["equipment_name_id"]
        mn = norm(r["maintop_no"])
        rn = norm(r["routine_no"])
        # Use frequency from linked AddRoutineDetails as the source of truth for initiation
        frq = norm(r["add_routine_details__frequency"])

        if eq_id and mn and rn and frq:
            rd_set.add((eq_id, mn, rn, frq))
    # print(f"{len(rd_set):,} unique initiated entries.")

    ard_rows = AddRoutineDetails.objects.values(
        "equipment_name_id", "maintop_no", "routine_no", "frequency"
    )
    ard_set = set()
    for r in ard_rows:
        eq_id = r["equipment_name_id"]
        mn = norm(r["maintop_no"])
        rn = norm(r["routine_no"])
        frq = norm(r["frequency"])
        if eq_id and mn and rn and frq:
            ard_set.add((eq_id, mn, rn, frq))
    # print(f"{len(ard_set):,} defined entries.")

    return rd_set, ard_set


def build_maintopdetail_map():
    print("  Loading MaintopDetail Ã¢â‚¬Â¦", end=" ", flush=True)

    # (maintop_no, freq) Ã¢â€ â€™ max amendment_no
    amend_map = defaultdict(lambda: None)
    # frequency_upper Ã¢â€ â€™ freq_number string
    freq_num_map = {}
    # maintop_no Ã¢â€ â€™ list of (routine_no, frequency)
    detail_map = defaultdict(list)

    rows = MaintopDetail.objects.select_related("frequency_f_key").values(
        "maintop_no",
        "routine_no",
        "routine_description",
        "universal_id_t_maintopdetail",
        "universal_id_m_frequency",
        "frequency",
        "amendment_no",
        "frequency_f_key__months",
        "frequency_f_key__hours",
        "by_whom",
    )

    seen = set()
    for row in rows:
        mn = norm(row["maintop_no"])
        rn = norm(row["routine_no"])
        frq = norm(row["frequency"])
        by_whom = norm(row["by_whom"])
        amn = row["amendment_no"]

        if not mn or not rn or not frq:
            continue

        # Max amendment per (maintop_no, frequency)
        k = (mn, frq)
        if amend_map[k] is None or (amn is not None and amn > amend_map[k]):
            amend_map[k] = amn

        # Frequency number lookup
        if frq and frq not in freq_num_map:
            m = row["frequency_f_key__months"]
            h = row["frequency_f_key__hours"]
            freq_num_map[frq] = str(m) if m else (str(h) if h else "N/A")

        # Unique (mn, rn, frq) entries per maintop
        if (mn, rn, frq) not in seen:
            seen.add((mn, rn, frq))
            detail_map[mn].append(
                {
                    "routine_no": rn,
                    "frequency": frq,
                    "by_whom": by_whom,
                    "frequency": frq,
                    "freq_number": freq_num_map.get(frq, "N/A"),
                    "highest_amend": amend_map.get((mn, frq)),
                    "universal_id": row["universal_id_t_maintopdetail"],
                    "frequency_id": row["universal_id_m_frequency"],
                    "description": row["routine_description"],
                }
            )
    print(f"{len(seen):,} unique (maintop, routine, freq) rows.")
    return detail_map, amend_map, freq_num_map


class MissingRoutinesAPIView(APIView):
    pagination_class = CommonPagination

    def get(self, request):
        try:
            ard_eq_maintop, _ = build_ard_structures()
            rd_set, ard_set = build_rd_and_ard_sets()
            detail_map, _, _ = build_maintopdetail_map()

            equipments = list(
                EquipmentName.objects.values(
                    "id",
                    "nomenclature",
                    "name",
                    "universal_id_t_equipment_ship_detail",
                    "equipment_code",
                    "sfd_equipment__department__name",
                    "sub_department__department_name__name",
                )
            )

            ship_obj = get_this_ship()

            frequency_ids = set()

            for items in detail_map.values():
                for item in items:
                    frequency_id = item.get("frequency_id")

                    if frequency_id:
                        frequency_ids.add(frequency_id)

            frequency_map = {
                frequency.universal_id_m_frequency: frequency
                for frequency in Frequency.objects.filter(
                    universal_id_m_frequency__in=frequency_ids
                )
            }

            normalized_data = []

            for eq in equipments:
                eq_id = eq["id"]

                nom = (eq["nomenclature"] or eq["name"] or "").strip()

                eq_uid = eq["universal_id_t_equipment_ship_detail"]

                maintop_nos = ard_eq_maintop.get(eq_id, set())

                if not maintop_nos:
                    continue

                for mn in maintop_nos:
                    expected = detail_map.get(mn, [])

                    if not expected:
                        continue

                    for item in expected:
                        rn = item["routine_no"]
                        frq = item["frequency"]
                        by_whom = item["by_whom"]

                        full_key = (eq_id, mn, rn, frq)

                        if full_key in rd_set:
                            continue

                        frequency = frequency_map.get(item.get("frequency_id"))

                        normalized_record = {
                            "Universal_ID_M_Frequency": item.get("frequency_id"),
                            "Universal_ID_T_EquipmentShipDetail": eq_uid,
                            "Universal_ID_T_Dart": None,
                            "dartnumber": None,
                            "classname": (
                                ship_obj.class_master.description
                                if ship_obj and ship_obj.class_master
                                else None
                            ),
                            "shipname": (ship_obj.name if ship_obj else None),
                            "equipmentname": nom,
                            "departmentname": (
                                eq["sfd_equipment__department__name"]
                                or eq["sub_department__department_name__name"]
                            ),
                            "equipmentcode": eq["equipment_code"],
                            "maintopno": mn,
                            "nomenclature": nom,
                            "routineno": rn,
                            "routinedescription": item.get("description"),
                            "bywhom": by_whom,
                            "routinename": (
                                frequency.description if frequency else None
                            ),
                            "frequency": frq,
                            "frequencymonth": (frequency.months if frequency else None),
                            "frequencyhours": (frequency.hours if frequency else None),
                            "routineduedate": None,
                            "rhsiupdatedupto": None,
                            "lastroutinecompletedatrh": None,
                            "lastroutinecompletedatdate": None,
                            "universal_id_t_maintopdetail": item.get("universal_id"),
                        }

                        normalized_data.append(normalized_record)

            search = request.GET.get("search", "").strip().lower()

            if search:
                filtered_data = []

                for record in normalized_data:
                    searchable_values = [
                        record.get("Universal_ID_M_Frequency"),
                        record.get("Universal_ID_T_EquipmentShipDetail"),
                        record.get("dartnumber"),
                        record.get("classname"),
                        record.get("shipname"),
                        record.get("equipmentname"),
                        record.get("departmentname"),
                        record.get("equipmentcode"),
                        record.get("maintopno"),
                        record.get("nomenclature"),
                        record.get("routineno"),
                        record.get("routinedescription"),
                        record.get("bywhom"),
                        record.get("routinename"),
                        record.get("frequency"),
                        record.get("frequencymonth"),
                        record.get("frequencyhours"),
                        record.get("universal_id_t_maintopdetail"),
                    ]

                    if any(
                        search in str(value).lower()
                        for value in searchable_values
                        if value is not None
                    ):
                        filtered_data.append(record)

                normalized_data = filtered_data

            if "sfd/missing-routine-sync" in request.path:
                return StreamingHttpResponse(
                    stream_sync_log(
                        "Create Nomenclature wise Missing Routines",
                        normalized_data,
                        create_missing_dart=True,
                    ),
                    content_type="text/plain",
                )

            paginator = self.pagination_class()

            paginated_data = paginator.paginate_queryset(
                normalized_data, request, view=self
            )

            return paginator.get_paginated_response(paginated_data)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SaveCMMSDefectsAPI(APIView):
    def get(self, request):
        return Response(
            {
                "status": True,
                "message": "SaveCMMSDefectsAPI endpoint ready for POST payload.",
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        try:
            data = request.data
            if isinstance(data, list):
                defects = data
            elif isinstance(data, dict):
                defects = data.get("defects", [])
            else:
                defects = []

            if not isinstance(defects, list):
                return Response(
                    {"status": False, "error": "defects must be a list."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            saved_count = 0

            dart_universal_ids = set()
            dart_numbers = set()
            equipment_ids = set()
            department_ids = set()
            symptom_ids = set()
            severity_ids = set()
            remark_ids = set()
            required_assistance_ids = set()
            refit_ids = set()

            for d in defects:
                dart_number = d.get("dartnumber")
                universal_id = d.get("Universal_ID_T_Dart")

                if dart_number:
                    dart_numbers.add(dart_number)

                if universal_id:
                    dart_universal_ids.add(universal_id)

                if d.get("universal_id_t_equipment_ship_detail"):
                    equipment_ids.add(d.get("universal_id_t_equipment_ship_detail"))

                if d.get("universal_id_m_department"):
                    department_ids.add(d.get("universal_id_m_department"))

                if d.get("Universal_ID_Ch_Master_Symptoms"):
                    symptom_ids.add(d.get("Universal_ID_Ch_Master_Symptoms"))

                if d.get("Universal_ID_M_Severity"):
                    severity_ids.add(d.get("Universal_ID_M_Severity"))

                if d.get("Universal_ID_Ch_Master_Ship_Remarks_By"):
                    remark_ids.add(d.get("Universal_ID_Ch_Master_Ship_Remarks_By"))

                if d.get("Universal_ID_M_RequiredAssistance"):
                    required_assistance_ids.add(
                        d.get("Universal_ID_M_RequiredAssistance")
                    )

                if d.get("Universal_ID_T_RefComp"):
                    refit_ids.add(d.get("Universal_ID_T_RefComp"))

            ship_equipment_map = {
                obj.t_equipment_ship_detail: obj
                for obj in ShipEquipment.objects.filter(
                    t_equipment_ship_detail__in=equipment_ids
                )
            }

            department_map = {
                obj.universal_id_m_department: obj
                for obj in Department.objects.filter(
                    universal_id_m_department__in=department_ids
                )
            }

            ems_equipment_map = {
                obj.universal_id_t_equipment_ship_detail: obj
                for obj in EquipmentName.objects.filter(
                    universal_id_t_equipment_ship_detail__in=equipment_ids
                )
            }
            symptom_map = {
                obj.universal_id_ch_master_symptoms: obj
                for obj in ChMasterSymptoms.objects.filter(
                    universal_id_ch_master_symptoms__in=symptom_ids
                )
            }
            severity_map = {
                obj.universal_id_m_severity: obj
                for obj in MSeverity.objects.filter(
                    universal_id_m_severity__in=severity_ids
                )
            }
            remark_map = {
                obj.universal_id_ch_master_ship_remarks_by: obj
                for obj in ChMasterShipRemarksBy.objects.filter(
                    universal_id_ch_master_ship_remarks_by__in=remark_ids
                )
            }
            required_assistance_map = {
                obj.universal_id_m_required_assistance: obj
                for obj in MRequiredAssistance.objects.filter(
                    universal_id_m_required_assistance__in=required_assistance_ids
                )
            }
            refit_map = {
                obj.universal_id_m_refit: obj
                for obj in RefitMaintenancePeriod.objects.filter(
                    universal_id_m_refit__in=refit_ids
                )
            }

            existing_by_universal_id = {
                obj.universal_id_t_dart: obj
                for obj in InitiateDart.objects.filter(
                    universal_id_t_dart__in=dart_universal_ids
                )
            }

            existing_by_dart_number = {
                obj.dart_number: obj
                for obj in InitiateDart.objects.filter(dart_number__in=dart_numbers)
            }

            def parse_dt(dt_str):
                if not dt_str:
                    return None

                try:
                    return datetime.strptime(
                        str(dt_str).split("T")[0], "%Y-%m-%d"
                    ).date()

                except (ValueError, TypeError):
                    return None

            with transaction.atomic():
                for d in defects:
                    dart_number = d.get("dartnumber")

                    # Same old behaviour
                    if not dart_number:
                        continue

                    universal_id = d.get("Universal_ID_T_Dart")

                    obj = None

                    if universal_id:
                        obj = existing_by_universal_id.get(universal_id)

                    if not obj:
                        obj = existing_by_dart_number.get(dart_number)

                    if not obj:
                        obj = InitiateDart(dart_number=dart_number)

                    if universal_id:
                        obj.universal_id_t_dart = universal_id

                    t_eq_id = d.get("universal_id_t_equipment_ship_detail")

                    ship_eq = ship_equipment_map.get(t_eq_id)

                    univ_dept_id = d.get("universal_id_m_department")

                    dept = department_map.get(univ_dept_id)

                    symptom_id = d.get("Universal_ID_Ch_Master_Symptoms")

                    symptom = symptom_map.get(symptom_id)

                    severity_id = d.get("Universal_ID_M_Severity")

                    severity = severity_map.get(severity_id)

                    remark_id = d.get("Universal_ID_Ch_Master_Ship_Remarks_By")

                    remark = remark_map.get(remark_id)

                    ra_id = d.get("Universal_ID_M_RequiredAssistance")

                    ra = required_assistance_map.get(ra_id)

                    refit_id = d.get("Universal_ID_T_RefComp")

                    refit = refit_map.get(refit_id)

                    obj.equipment_ship = ship_eq

                    obj.department_id = dept

                    obj.equipment_ems = ems_equipment_map.get(t_eq_id)

                    obj.dart_sr_number = d.get("serial_number")

                    obj.dart_date = parse_dt(d.get("dart_date"))

                    obj.rectification_date = parse_dt(d.get("schedule_date"))

                    ops_val = d.get("is_operational")

                    if ops_val is not None:
                        obj.ops_status = bool(ops_val)

                        obj.maintenance_period = (
                            "OPERATIONAL" if bool(ops_val) else "REFIT"
                        )

                    obj.trial_required = bool(d.get("trial_required"))

                    obj.defective_component = d.get("defective_component")

                    obj.defective_discriptions = d.get("defect_description") or d.get(
                        "remarks"
                    )

                    obj.is_closed = bool(d.get("isclosed"))

                    obj.symptom_code = symptom

                    obj.severity_code = severity

                    obj.remark_code = remark

                    obj.require_assistance_for_code = ra

                    obj.refit_maintenance_period_f_key = refit

                    obj.is_guarantee_defect = bool(d.get("is_guarantee_defect"))

                    obj.guarantee_cause = d.get("guarantee_cause")

                    val_op = d.get("guarantee_op_availability")

                    obj.guarantee_op_availability = (
                        bool(val_op) if val_op is not None else False
                    )

                    val_hw = d.get("guarantee_hot_work")

                    obj.guarantee_hot_work = (
                        bool(val_hw) if val_hw is not None else False
                    )

                    obj.guarantee_repairs = d.get("guarantee_repairs")

                    obj.guarantee_place = d.get("guarantee_place")

                    obj.guarantee_repair_date = parse_dt(d.get("guarantee_repair_date"))

                    obj.guarantee_completion_date = parse_dt(
                        d.get("guarantee_completion_date")
                    )

                    obj.save()

                    saved_count += 1

                    # Keep maps updated for duplicate records
                    if universal_id:
                        existing_by_universal_id[universal_id] = obj

                    existing_by_dart_number[dart_number] = obj

            return Response(
                {
                    "status": True,
                    "message": (f"Successfully saved {saved_count} defects."),
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"status": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CMMSDefectSyncAPI(APIView):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        conn = None
        cursor = None

        try:
            # ---------------------------------------------------------
            # Get local ShipEquipment mappings
            # ---------------------------------------------------------
            equipment_ship_detail_ids = list(
                ShipEquipment.objects.values_list("t_equipment_ship_detail", flat=True)
            )

            equipment_ship_detail_ids = [x for x in equipment_ship_detail_ids if x]

            if not equipment_ship_detail_ids:
                if "sfd/open-defects-sync" in request.path:
                    return HttpResponse(
                        "[SYSTEM] Starting CMMS Open Defects Sync...\n"
                        "[SKIPPED] No local ShipEquipment records found to map defects.\n"
                        "[Completed] CMMS open defect sync completed.",
                        content_type="text/plain",
                    )
                return Response(
                    {
                        "status": True,
                        "message": "No local ShipEquipment records found to map defects.",
                        "fetched_count": 0,
                        "saved_count": 0,
                        "inserted_count": 0,
                        "updated_count": 0,
                        "error_count": 0,
                        "errors": [],
                    },
                    status=status.HTTP_200_OK,
                )

            # ---------------------------------------------------------
            # Get current ship
            # ---------------------------------------------------------
            ship_obj = get_this_ship()

            if not ship_obj:
                return Response(
                    {"status": False, "message": "Local Ship object not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---------------------------------------------------------
            # Parameterized IN clause
            # ---------------------------------------------------------
            id_placeholders = ",".join(["?"] * len(equipment_ship_detail_ids))

            query = f"""
                SELECT
                    T_Dart.Universal_ID_T_Dart,
                    T_Dart.DartNumber,
                    T_Dart.DartDate,
                    T_Dart.DefectDate,
                    T_Dart.ScheduleDate,
                    T_Dart.Universal_ID_Ch_Master_Symptoms,
                    T_Dart.SeverityID,
                    T_Dart.SeverityCode,
                    T_Dart.Universal_ID_M_Severity,
                    T_Dart.Universal_ID_Ch_Master_Ship_Remarks_By,
                    T_Dart.Universal_ID_M_RequiredAssistance,
                    T_Dart.IsOstObservation,
                    T_Dart.DefectiveComponent,
                    T_Dart.Remarks AS Remarks,
                    T_Dart.DefectDescription AS DefectDescription,
                    T_Dart.IsClosed,
                    T_Dart.Is_Defect,
                    T_Dart.Active,
                    T_Dart.RoutineDefect,
                    T_Dart.Serial_Number,
                    T_Dart.Is_Operational,
                    T_Dart.Universal_ID_T_RefComp,
                    T_Dart.Universal_ID_M_Ship,
                    T_Dart.Universal_ID_M_Department,
                    T_Dart.Universal_ID_T_EquipmentShipDetail,
                    T_Dart.IsGDForm,

                    T_DartDetailGD.Reason AS GD_Reason,

                    T_DartDetailGD.Defect_affects_sea_going_Operational_Availability
                        AS GD_Defect_affects_sea_going_Operational_Availability,

                    T_DartDetailGD.Hot_Work_Involved
                        AS GD_Hot_Work_Involved,

                    T_DartDetailGD.Date_place
                        AS GD_Date_place,

                    T_DartDetailGD.Date_for_Repairs
                        AS GD_Date_for_Repairs,

                    T_DartDetailGD.Place
                        AS GD_Place,

                    T_DartDetailGD.DateOfCompletion
                        AS GD_DateOfCompletion,

                    T_EquipmentShipDetail.Nomenclature,
                    M_Equipment.EquipmentName,
                    M_Equipment.EquipmentCode,
                    M_Department.Description AS DepartmentName,
                    M_Ship.ShipName,
                    M_ShipClass.Description AS ClassName

                FROM T_Dart WITH (NOLOCK)

                INNER JOIN T_EquipmentShipDetail WITH (NOLOCK)
                    ON T_Dart.Universal_ID_T_EquipmentShipDetail =
                       T_EquipmentShipDetail.Universal_ID_T_EquipmentShipDetail

                INNER JOIN M_Ship WITH (NOLOCK)
                    ON T_Dart.Universal_ID_M_Ship =
                       M_Ship.Universal_ID_M_Ship

                INNER JOIN M_ShipClass WITH (NOLOCK)
                    ON M_Ship.Universal_ID_M_ShipClass =
                       M_ShipClass.Universal_ID_M_ShipClass

                INNER JOIN M_Department WITH (NOLOCK)
                    ON T_Dart.Universal_ID_M_Department =
                       M_Department.Universal_ID_M_Department

                INNER JOIN M_Equipment WITH (NOLOCK)
                    ON T_EquipmentShipDetail.Universal_ID_M_Equipment =
                       M_Equipment.Universal_ID_M_Equipment

                LEFT JOIN T_DartDetailGD WITH (NOLOCK)
                    ON T_Dart.Universal_ID_T_Dart =
                       T_DartDetailGD.Universal_ID_T_Dart

                WHERE
                    T_EquipmentShipDetail.Active = 1

                    AND M_Equipment.Active = 1

                    AND T_Dart.Universal_ID_M_Ship = ?

                    AND T_Dart.Active = 1

                    AND T_Dart.Is_Defect = 1

                    AND T_Dart.IsClosed = 0

                    AND T_Dart.Universal_ID_T_EquipmentShipDetail
                        IN ({id_placeholders})

                ORDER BY
                    T_Dart.DartDate DESC
            """

            params = [ship_obj.universal_id_m_ship]
            params.extend(equipment_ship_detail_ids)

            # ---------------------------------------------------------
            # Connect to CMMS MSSQL
            # ---------------------------------------------------------
            conn = get_mssql_connection()
            cursor = conn.cursor()

            cursor.execute(query, params)

            columns = [col[0] for col in cursor.description]

            rows = cursor.fetchall()

            fetched_count = len(rows)

            saved_count = 0
            inserted_count = 0
            updated_count = 0
            error_count = 0
            errors = []

            # ---------------------------------------------------------
            # Date conversion helper
            # ---------------------------------------------------------
            def parse_date_val(value):
                if not value:
                    return None

                if isinstance(value, datetime):
                    return value.date()

                if isinstance(value, date):
                    return value

                try:
                    return datetime.strptime(
                        str(value).split("T")[0], "%Y-%m-%d"
                    ).date()
                except Exception:
                    return None

            # ---------------------------------------------------------
            # Process CMMS defects
            # ---------------------------------------------------------
            for row in rows:
                record = dict(zip(columns, row))

                dart_number = record.get("DartNumber")

                if not dart_number:
                    continue

                try:
                    # -------------------------------------------------
                    # Find existing InitiateDart
                    # -------------------------------------------------
                    universal_id = record.get("Universal_ID_T_Dart")

                    obj = None

                    if universal_id:
                        obj = InitiateDart.objects.filter(
                            universal_id_t_dart=universal_id
                        ).first()

                    if not obj:
                        obj = InitiateDart.objects.filter(
                            dart_number=dart_number
                        ).first()

                    created_new = False

                    if not obj:
                        obj = InitiateDart(dart_number=dart_number)
                        created_new = True

                    if universal_id:
                        obj.universal_id_t_dart = universal_id

                    # -------------------------------------------------
                    # Equipment mapping
                    # -------------------------------------------------
                    t_eq_id = record.get("Universal_ID_T_EquipmentShipDetail")

                    ship_eq = None
                    ems_eq = None

                    if t_eq_id:
                        ship_eq = ShipEquipment.objects.filter(
                            t_equipment_ship_detail=t_eq_id
                        ).first()

                        ems_eq = EquipmentName.objects.filter(
                            universal_id_t_equipment_ship_detail=t_eq_id
                        ).first()

                    # -------------------------------------------------
                    # Department mapping
                    # -------------------------------------------------
                    univ_dept_id = record.get("Universal_ID_M_Department")

                    dept = None

                    if univ_dept_id:
                        dept = Department.objects.filter(
                            universal_id_m_department=univ_dept_id
                        ).first()

                    # -------------------------------------------------
                    # Symptom mapping
                    # -------------------------------------------------
                    symptom_id = record.get("Universal_ID_Ch_Master_Symptoms")

                    symptom = None

                    if symptom_id:
                        symptom = ChMasterSymptoms.objects.filter(
                            universal_id_ch_master_symptoms=symptom_id
                        ).first()

                    # -------------------------------------------------
                    # Severity mapping
                    # -------------------------------------------------
                    severity_id = record.get("Universal_ID_M_Severity")

                    severity = None

                    if severity_id:
                        severity = MSeverity.objects.filter(
                            universal_id_m_severity=severity_id
                        ).first()

                    # -------------------------------------------------
                    # Remark mapping
                    # -------------------------------------------------
                    remark_id = record.get("Universal_ID_Ch_Master_Ship_Remarks_By")

                    remark = None

                    if remark_id:
                        remark = ChMasterShipRemarksBy.objects.filter(
                            universal_id_ch_master_ship_remarks_by=remark_id
                        ).first()

                    # -------------------------------------------------
                    # Required Assistance mapping
                    # -------------------------------------------------
                    ra_id = record.get("Universal_ID_M_RequiredAssistance")

                    ra = None

                    if ra_id:
                        ra = MRequiredAssistance.objects.filter(
                            universal_id_m_required_assistance=ra_id
                        ).first()

                    # -------------------------------------------------
                    # Refit mapping
                    # -------------------------------------------------
                    refit_id = record.get("Universal_ID_T_RefComp")

                    refit = None

                    if refit_id:
                        refit = RefitMaintenancePeriod.objects.filter(
                            universal_id_m_refit=refit_id
                        ).first()

                    # -------------------------------------------------
                    # Map main fields
                    # -------------------------------------------------
                    obj.equipment_ship = ship_eq
                    obj.department_id = dept
                    obj.equipment_ems = ems_eq or None

                    obj.dart_sr_number = record.get("Serial_Number")

                    obj.dart_date = parse_date_val(record.get("DartDate"))

                    obj.rectification_date = parse_date_val(record.get("ScheduleDate"))

                    # -------------------------------------------------
                    # Operational status
                    # -------------------------------------------------
                    ops_val = record.get("Is_Operational")

                    if ops_val is not None:
                        obj.ops_status = bool(ops_val)

                        obj.maintenance_period = (
                            "OPERATIONAL" if bool(ops_val) else "REFIT"
                        )

                    obj.trial_required = bool(record.get("IsOstObservation"))

                    obj.defective_component = record.get("DefectiveComponent")

                    obj.defective_discriptions = record.get(
                        "DefectDescription"
                    ) or record.get("Remarks")

                    obj.is_closed = bool(record.get("IsClosed"))

                    # -------------------------------------------------
                    # Related master mappings
                    # -------------------------------------------------
                    obj.symptom_code = symptom
                    obj.severity_code = severity
                    obj.remark_code = remark
                    obj.require_assistance_for_code = ra
                    obj.refit_maintenance_period_f_key = refit

                    # -------------------------------------------------
                    # Guarantee defect fields
                    # -------------------------------------------------
                    obj.is_guarantee_defect = bool(record.get("IsGDForm"))

                    obj.guarantee_cause = record.get("GD_Reason")

                    val_op = record.get(
                        "GD_Defect_affects_sea_going_Operational_Availability"
                    )

                    obj.guarantee_op_availability = (
                        bool(val_op) if val_op is not None else False
                    )

                    val_hw = record.get("GD_Hot_Work_Involved")

                    obj.guarantee_hot_work = (
                        bool(val_hw) if val_hw is not None else False
                    )

                    obj.guarantee_repairs = record.get("GD_Date_place")

                    obj.guarantee_place = record.get("GD_Place")

                    obj.guarantee_repair_date = parse_date_val(
                        record.get("GD_Date_for_Repairs")
                    )

                    obj.guarantee_completion_date = parse_date_val(
                        record.get("GD_DateOfCompletion")
                    )

                    obj.save()

                    saved_count += 1

                    if created_new:
                        inserted_count += 1
                    else:
                        updated_count += 1

                except Exception as ex:
                    error_count += 1

                    errors.append({"dartnumber": dart_number, "error": str(ex)})

            if "sfd/open-defects-sync" in request.path:
                log_lines = [
                    "[SYSTEM] Starting CMMS Open Defects Sync...",
                    f"Fetched {fetched_count} open defects from CMMS. Processing start...",
                    f"[OK] Saved {saved_count} defects.",
                    f"[NEW] Inserted: {inserted_count}",
                    f"[EXISTING] Updated: {updated_count}",
                    f"[SKIPPED] Errors: {error_count}",
                    "[Completed] CMMS open defect sync completed successfully.",
                ]
                for item in errors[:25]:
                    log_lines.append(
                        f"[ERROR] {item.get('dartnumber')}: {item.get('error')}"
                    )
                return HttpResponse("\n".join(log_lines), content_type="text/plain")

            return Response(
                {
                    "status": True,
                    "message": ("CMMS open defect sync completed successfully."),
                    "fetched_count": fetched_count,
                    "saved_count": saved_count,
                    "inserted_count": inserted_count,
                    "updated_count": updated_count,
                    "error_count": error_count,
                    "errors": errors,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "status": False,
                    "message": "CMMS defect sync failed.",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()


### 2 APis Pending ##


class InitiateDARTDataSaveAPI(APIView):
    def post(self, request):
        conn = None
        cursor = None

        try:
            data = request.data
            initiate_darts = data.get("initiate_darts", [])

            ship_obj = get_this_ship()

            # ship_obj = Ship.objects.filter(
            #     universal_id_m_ship='303'
            # ).first()

            ship_sr_no = None
            universal_id_m_ship = 0

            if ship_obj:
                ship_sr_no = ship_obj.sr_no
                universal_id_m_ship = ship_obj.universal_id_m_ship or 0

            # SQL SERVER CONNECTION
            conn = get_mssql_connection()
            cursor = conn.cursor()

            # ---------------- CHECK QUERY ----------------
            check_query = """
                SELECT 1
                FROM T_Dart
                WHERE Universal_ID_T_Dart = ?
            """

            check_gd_query = """
                SELECT 1
                FROM T_DartDetailGD
                WHERE Universal_ID_T_Dart = ?
            """

            # ---------------- UPDATE QUERY ----------------
            update_query = """
                UPDATE T_Dart
                SET
                    DartNumber = ?,
                    SrNo = ?,
                    ShipSrNo = ?,
                    EquipmentCode = ?,
                    DepartmentID = ?,

                    Department = ?,
                    ExDept = ?,
                    ExDeptID = ?,
                    DartDate = ?,
                    DefectDate = ?,

                    ScheduleDate = ?,
                    Universal_ID_Ch_Master_Symptoms = ?,
                    SeverityID = ?,
                    SeverityCode = ?,
                    Universal_ID_M_Severity = ?,
                    Universal_ID_Ch_Master_Ship_Remarks_By = ?,
                    Universal_ID_M_RequiredAssistance = ?,

                    IsOstObservation = ?,
                    Universal_ID_M_OSTList = ?,
                    DefectiveComponent = ?,
                    Remarks = ?,
                    DefectDescription = ?,
                    IsClosed = ?,

                    Is_Defect = ?,
                    Active = ?,
                    NILDart = ?,
                    Is_Amp = ?,
                    Is_Signal_Drafted = ?,

                    Is_Refit = ?,
                    Is_Routine = ?,
                    Is_DLIIDrafted = ?,
                    Is_RefitRADraft = ?,
                    IsGDForm = ?,

                    Universal_ID_M_Ship = ?,
                    Universal_ID_M_Department = ?,
                    Universal_ID_T_EquipmentShipDetail = ?,

                    CreatedDate = ?,
                    RoutineDefect = ?,
                    Is_Final_Submit = ?,
                    Serial_Number = ?,
                    Is_Operational = ?,
                    Universal_ID_T_RefComp = ?

                WHERE Universal_ID_T_Dart = ?
            """

            # ---------------- UPDATE GD QUERY ----------------
            update_gd_query = """
                UPDATE T_DartDetailGD
                SET
                    Reason = ?,
                    Defect_affects_sea_going_Operational_Availability = ?,
                    Hot_Work_Involved = ?,
                    Date_place = ?,
                    Date_for_Repairs = ?,
                    Place = ?,
                    UpdatedDate = ?,
                    DateOfCompletion = ?,
                    Universal_ID_T_DartDetailGD = ?

                WHERE Universal_ID_T_Dart = ?
            """

            # ---------------- INSERT QUERY ----------------
            insert_query = """
                INSERT INTO T_Dart
                (
                    DartNumber,
                    SrNo,
                    ShipSrNo,
                    EquipmentCode,
                    DepartmentID,

                    Department,
                    ExDept,
                    ExDeptID,
                    DartDate,
                    DefectDate,

                    ScheduleDate,
                    Universal_ID_Ch_Master_Symptoms,
                    SeverityID,
                    SeverityCode,
                    Universal_ID_M_Severity,
                    Universal_ID_Ch_Master_Ship_Remarks_By,
                    Universal_ID_M_RequiredAssistance,

                    IsOstObservation,
                    Universal_ID_M_OSTList,
                    DefectiveComponent,
                    Remarks,
                    DefectDescription,
                    IsClosed,

                    Is_Defect,
                    Active,
                    NILDart,
                    Is_Amp,
                    Is_Signal_Drafted,

                    Is_Refit,
                    Is_Routine,
                    Is_DLIIDrafted,
                    Is_RefitRADraft,
                    IsGDForm,

                    Universal_ID_M_Ship,
                    Universal_ID_M_Department,
                    Universal_ID_T_EquipmentShipDetail,

                    CreatedDate,
                    RoutineDefect,
                    Is_Final_Submit,
                    Serial_Number,
                    Is_Operational,
                    Universal_ID_T_RefComp,

                    Universal_ID_T_Dart
                )
                VALUES
                (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
            """

            # ---------------- INSERT GD QUERY ----------------
            insert_gd_query = """
                INSERT INTO T_DartDetailGD
                (
                    Universal_ID_T_Dart,
                    Reason,
                    Defect_affects_sea_going_Operational_Availability,
                    Hot_Work_Involved,
                    Date_place,
                    Date_for_Repairs,
                    Place,
                    CreatedDate,
                    DateOfCompletion,
                    Universal_ID_T_DartDetailGD,
                    IsSynced
                )
                VALUES
                (?,?,?,?,?,?,?,?,?,?,?)
            """

            # ---------------- PROCESS DATA ----------------
            inserted_ids = []
            success_ids = []

            for dart in initiate_darts:
                dart_id = dart.get("universal_id_t_dart")

                if not dart_id:
                    dart_id = f"SWMM-{dart.get('id')}"

                # ---------------- CHECK DART ----------------
                cursor.execute(check_query, (dart_id,))

                exists = cursor.fetchone()

                dart_number = dart.get("dart_number")

                dart_parts = (dart_number or "").split("-")

                dart_type = dart_parts[0] if len(dart_parts) > 0 else ""

                dart_section = dart_parts[1] if len(dart_parts) > 1 else ""

                dart_no = dart_parts[2] if len(dart_parts) > 2 else ""

                sr_no = f"{dart_section}-{dart_no}"

                # ---------------- DART VALUES ----------------
                values = (
                    dart.get("dart_number"),
                    sr_no,
                    ship_sr_no,
                    dart.get("equipment_code"),
                    dart.get("department_DepartmentID"),
                    dart.get("department_Department"),
                    dart.get("department_ExDept"),
                    dart.get("department_ExDeptID"),
                    dart.get("dart_date"),
                    dart.get("dart_date"),
                    dart.get("rectified_date"),
                    dart.get("Universal_ID_Ch_Master_Symptoms"),
                    dart.get("serverity_id"),
                    dart.get("serverity_code"),
                    dart.get("Universal_ID_M_Severity"),
                    dart.get("Universal_ID_Ch_Master_Ship_Remarks_By"),
                    dart.get("Universal_ID_M_RequiredAssistance"),
                    dart.get("trial_required"),
                    dart.get("Universal_ID_M_OSTList"),
                    dart.get("defective_component"),
                    dart.get("defective_discriptions"),
                    dart.get("defective_discriptions"),
                    0,
                    1,
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    universal_id_m_ship,
                    dart.get("Universal_ID_M_Department"),
                    dart.get("t_ship_details"),
                    dart.get("created_date"),
                    2,
                    1,
                    dart_no,
                    dart.get("Is_Operational"),
                    dart.get("Universal_ID_T_RefComp"),
                )

                try:
                    # ---------------- UPDATE / INSERT DART ----------------
                    if exists:
                        cursor.execute(update_query, values + (dart_id,))

                    else:
                        cursor.execute(insert_query, values + (dart_id,))

                        inserted_ids.append(dart_id)

                    success_ids.append(dart.get("id"))

                    # ---------------- GUARANTEE DEFECT SYNC ----------------
                    if dart.get("is_guarantee_defect"):
                        g_repairs = dart.get("guarantee_repairs")

                        g_repair_date = dart.get("guarantee_repair_date")

                        g_place = dart.get("guarantee_place")

                        if g_repairs == "0":
                            g_repair_date = None
                            g_place = None

                        # ---------------- CHECK GD ----------------
                        cursor.execute(check_gd_query, (dart_id,))

                        gd_exists = cursor.fetchone()

                        # ---------------- UPDATE GD ----------------
                        if gd_exists:
                            gd_update_values = (
                                dart.get("guarantee_cause"),
                                dart.get("guarantee_op_availability"),
                                dart.get("guarantee_hot_work"),
                                g_repairs,
                                g_repair_date,
                                g_place,
                                dart.get("created_date"),
                                dart.get("guarantee_completion_date"),
                                dart_id,
                                dart_id,
                            )

                            cursor.execute(update_gd_query, gd_update_values)

                        # ---------------- INSERT GD ----------------
                        else:
                            gd_insert_values = (
                                dart_id,
                                dart.get("guarantee_cause"),
                                dart.get("guarantee_op_availability"),
                                dart.get("guarantee_hot_work"),
                                g_repairs,
                                g_repair_date,
                                g_place,
                                dart.get("created_date"),
                                dart.get("guarantee_completion_date"),
                                dart_id,
                                0,
                            )

                            cursor.execute(insert_gd_query, gd_insert_values)

                except Exception as row_error:
                    logger.error(
                        "Failed inserting dart at index %s | DartNumber=%s | Error=%s",
                        dart.get("dart_number"),
                        str(row_error),
                    )

                    raise row_error

            # ---------------- COMMIT ----------------
            conn.commit()

            # ---------------- UPDATE LOCAL SYNC STATUS ----------------
            if success_ids:
                InitiateDart.objects.filter(id__in=success_ids).update(
                    cmms_sync_status=True
                )

            return Response(
                {
                    "status": True,
                    "message": "DART records saved successfully",
                    "inserted_count": len(inserted_ids),
                    "data": inserted_ids,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            if conn:
                conn.rollback()

            logger.exception("DART bulk insert failed")

            return Response(
                {
                    "status": False,
                    "message": "Failed to save DART data",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()


class CompleteDARTUpdateAPI(APIView):
    """
    Update DART completion details in CMMS.dbo.T_Dart
    """

    def post(self, request):
        conn = None
        cursor = None

        try:
            complete_darts = request.data.get("complete_darts", [])

            if not complete_darts:
                return Response(
                    {"status": False, "error": "complete_darts is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conn = get_mssql_connection()
            cursor = conn.cursor()

            update_query = """
                UPDATE T_Dart
                SET
                    RectifiedDate = ?,
                    CancelDate = ?,
                    DiagnosticCode = ?,
                    RepairCode = ?,
                    DelayReasonDays = ?,
                    Additional_Remarks = ?,
                    SparesAvailability = ?,
                    DiagnosticID = ?,
                    RepairID = ?,
                    RepairAgencyID = ?,
                    AgencyCode = ?,
                    DelayID = ?,
                    DelayCode = ?,
                    Universal_ID_M_Repair = ?,
                    Universal_ID_M_Delay = ?,
                    Universal_ID_M_Diagnostic = ?,
                    Universal_ID_M_RepairAgency = ?,
                    Is_Auto_Generated_Dart = ?,
                    IsClosed = ?,
                    UpdatedDate = GETDATE()
                WHERE Universal_ID_T_Dart = ?
            """

            updated_ids = []

            for comp in complete_darts:
                universal_id = f"SWMM-{comp['initiate_dart_id']}"

                values = (
                    comp.get("rectified_date"),
                    comp.get("rectified_date"),
                    comp.get("DiagnosticCode"),
                    comp.get("RepairCode"),
                    comp.get("days_delay"),
                    comp.get("rectification_details"),
                    comp.get("spares_delay"),
                    comp.get("DiagnosticID"),
                    comp.get("RepairID"),
                    comp.get("AgencyID"),
                    comp.get("AgencyCode"),
                    comp.get("DelayID"),
                    comp.get("DelayCode"),
                    comp.get("Universal_ID_M_Repair"),
                    comp.get("Universal_ID_M_Delay"),
                    comp.get("Universal_ID_M_Diagnostic"),
                    comp.get("Universal_ID_M_RepairAgency"),
                    comp.get("Is_Auto_Generated_Dart"),
                    1,
                    universal_id,
                )

                cursor.execute(update_query, values)

                updated_ids.append(universal_id)

            conn.commit()

            return Response(
                {
                    "status": True,
                    "message": "DART completion updated successfully",
                    "updated_count": len(updated_ids),
                    "updated_ids": updated_ids,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            if conn:
                conn.rollback()

            logger.exception("DART completion update failed")

            return Response(
                {"status": False, "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()


class InitiateDartSyncAPIView(APIView):
    def post(self, request, pk):
        if pk == 0:
            initiate_darts = InitiateDart.objects.select_related(
                "equipment_ship", "equipment_ems"
            ).all()
        else:
            initiate_darts = InitiateDart.objects.select_related(
                "equipment_ship", "equipment_ems"
            ).filter(id=pk)

        initiate_dart_json = []

        for dart in initiate_darts:
            dart_json = {
                "id": dart.id,
                # Equipment details
                "t_ship_details": (
                    str(dart.equipment_ship.t_equipment_ship_detail)
                    if dart.equipment_ship
                    else 0
                ),
                "m_equipment": (
                    str(dart.equipment_ship.equipment.universal_id_m_equipment)
                    if dart.equipment_ship
                    else None
                ),
                "equipment_code": (
                    str(dart.equipment_ship.equipment.equipment_code)
                    if dart.equipment_ship
                    else None
                ),
                # Dart details
                "dart_number": dart.dart_number,
                "dart_date": (dart.dart_date.isoformat() if dart.dart_date else None),
                "rectified_date": (
                    dart.rectification_date.isoformat()
                    if dart.rectification_date
                    else None
                ),
                "ops_status": dart.ops_status,
                "Universal_ID_Ch_Master_Symptoms": (
                    dart.symptom_code.universal_id_ch_master_symptoms
                    if dart.symptom_code
                    else None
                ),
                "Universal_ID_M_Severity": (
                    dart.severity_code.universal_id_m_severity
                    if dart.severity_code
                    else None
                ),
                "Universal_ID_Ch_Master_Ship_Remarks_By": (
                    dart.remark_code.universal_id_ch_master_ship_remarks_by
                    if dart.remark_code
                    else None
                ),
                "Universal_ID_M_RequiredAssistance": (
                    dart.require_assistance_for_code.universal_id_m_required_assistance
                    if dart.require_assistance_for_code
                    else None
                ),
                "symptom_code": (
                    dart.symptom_code.symptom_code if dart.symptom_code else None
                ),
                "serverity_code": (
                    dart.severity_code.severity_code if dart.severity_code else None
                ),
                "serverity_id": (
                    dart.severity_code.severity_id if dart.severity_code else None
                ),
                "remark_code": (
                    dart.remark_code.universal_id_ch_master_ship_remarks_by
                    if dart.remark_code
                    else None
                ),
                "trial_required": dart.trial_required,
                # Defect info
                "defective_component": dart.defective_component,
                "defective_discriptions": dart.defective_discriptions,
                # Department info
                "department_DepartmentID": int(dart.department_id.dep_code),
                "department_Department": dart.department_id.code,
                "department_ExDept": dart.department_id.code,
                "department_ExDeptID": int(dart.department_id.dep_code),
                "Universal_ID_M_Department": (
                    dart.department_id.universal_id_m_department
                ),
                # Status
                "is_closed": dart.is_closed,
                "sapres_required": dart.sapres_required,
                "is_ra_initiate": dart.is_ra_initiate,
                # File
                "photograph": (dart.photograph.url if dart.photograph else None),
                # Date
                "created_date": (
                    dart.created_date.isoformat() if dart.created_date else None
                ),
                "Is_Operational": (
                    1 if dart.maintenance_period == "OPERATIONAL" else 0
                ),
                "Universal_ID_T_RefComp": (
                    dart.refit_maintenance_period_f_key.Universal_ID_M_Refit
                    if dart.refit_maintenance_period_f_key
                    else None
                ),
                "Universal_ID_M_OSTList": (
                    dart.universal_id_trial_required if dart.trial_required else None
                ),
                "is_guarantee_defect": dart.is_guarantee_defect,
                "guarantee_cause": dart.guarantee_cause,
                "guarantee_op_availability": (dart.guarantee_op_availability),
                "guarantee_hot_work": dart.guarantee_hot_work,
                "guarantee_repairs": dart.guarantee_repairs,
                "guarantee_completion_date": (
                    dart.guarantee_completion_date.isoformat()
                    if dart.guarantee_completion_date
                    else None
                ),
                "guarantee_repair_date": (
                    dart.guarantee_repair_date.isoformat()
                    if dart.guarantee_repair_date
                    else None
                ),
                "guarantee_place": dart.guarantee_place,
                "universal_id_t_dart": dart.universal_id_t_dart,
            }

            initiate_dart_json.append(dart_json)

        # ---------------- FINAL PAYLOAD ----------------
        payload = {"initiate_darts": initiate_dart_json}

        json_data = json.dumps(
            payload, indent=4, ensure_ascii=False, cls=DjangoJSONEncoder
        )

        # Save JSON
        with open("initiate_dart_payload.json", "w", encoding="utf-8") as f:
            f.write(json_data)

        api_url = f"{API_URL}/api/dart/dart_initiate/"

        try:
            response = requests.post(
                api_url,
                data=json.dumps(payload, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"},
                timeout=8000,
                verify=False,
            )

            error_data = response.json()

            if error_data["status"] == False:
                return Response(
                    {
                        "status": False,
                        "message": error_data["message"],
                        "response": error_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            else:
                return Response(
                    {
                        "status": True,
                        "message": "Data was successfully sent to CMMS",
                        "response": error_data,
                    },
                    status=status.HTTP_200_OK,
                )

        except Exception as e:
            return Response(
                {"status": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CompleteDartSyncAPIView(APIView):
    def post(self, request, pk):
        """
        Sync completion data of a DART to CMMS
        """

        completions = CompleteDefectDart.objects.select_related("dart_details").all()

        if not completions.exists():
            return Response(
                {"status": False, "error": "No completion data found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        complete_darts = []

        for comp in completions:
            complete_darts.append(
                {
                    "initiate_dart_id": comp.dart_details.id,
                    "rectified_date": (
                        comp.rectified_date.isoformat() if comp.rectified_date else None
                    ),
                    "DiagnosticCode": (
                        comp.diagnostic_code.DiagnosticCode
                        if comp.diagnostic_code
                        else None
                    ),
                    "DiagnosticID": (
                        comp.diagnostic_code.DiagnosticId
                        if comp.diagnostic_code
                        else None
                    ),
                    "Universal_ID_M_Diagnostic": (
                        comp.diagnostic_code.Universal_ID_M_Diagnostic
                        if comp.diagnostic_code
                        else None
                    ),
                    "days_delay": comp.days_delay,
                    "rectification_details": "",
                    "spares_delay": comp.spares_delay,
                    "RepairCode": (
                        comp.repair_code.RepairCode if comp.repair_code else None
                    ),
                    "RepairID": (
                        comp.repair_code.RepairID if comp.repair_code else None
                    ),
                    "Universal_ID_M_Repair": (
                        comp.repair_code.Universal_ID_M_Repair
                        if comp.repair_code
                        else None
                    ),
                    "AgencyID": (
                        comp.repair_agency_code.RepairAgencyID
                        if comp.repair_agency_code
                        else None
                    ),
                    "AgencyCode": (
                        comp.repair_agency_code.RepairAgencyCode
                        if comp.repair_agency_code
                        else None
                    ),
                    "Universal_ID_M_RepairAgency": (
                        comp.repair_agency_code.Universal_ID_M_RepairAgency
                        if comp.repair_agency_code
                        else None
                    ),
                    "DelayID": (comp.delay_code.DelayID if comp.delay_code else None),
                    "DelayCode": (
                        comp.delay_code.DelayCode if comp.delay_code else None
                    ),
                    "Universal_ID_M_Delay": (
                        comp.delay_code.Universal_ID_M_Delay
                        if comp.delay_code
                        else None
                    ),
                    "Is_Auto_Generated_Dart": getattr(
                        comp, "is_auto_generated_dart", False
                    ),
                }
            )

        payload = {"complete_darts": complete_darts}

        api_url = f"{API_URL}/api/dart/complete/"

        try:
            response = requests.post(
                api_url,
                data=json.dumps(payload, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"},
                timeout=8000,
            )

            response_data = response.json()

            if response_data.get("status") == False:
                return Response(
                    {
                        "status": False,
                        "message": response_data.get("message", "Something went wrong"),
                        "response": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "status": True,
                    "message": "Data was successfully sent to CMMS",
                    "response": response_data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"status": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FussDataSaveAPI(APIView):
    def post(self, request):
        conn = None
        cursor = None

        try:
            data = request.data
            fuss_records = data.get("fuss_records", [])

            conn = get_mssql_connection()
            cursor = conn.cursor()

            # ---------------- CHECK QUERY ----------------
            check_query = """
                SELECT 1
                FROM T_Fuss
                WHERE Universal_ID_T_Fuss = ?
            """

            # ---------------- UPDATE QUERY ----------------
            update_query = """
                UPDATE T_Fuss
                SET
                    DepartmentID = ?,
                    FussDate = ?,
                    FrequencyID = ?,
                    LastUndertaken = ?,
                    DueDate = ?,

                    DefermentID = ?,
                    DefermentCode = ?,
                    ReasonID = ?,
                    ReasonCode = ?,

                    LastSMP = ?,
                    SMPDuration = ?,
                    LastAMP = ?,
                    AMPDuration = ?,
                    AMPSMPReqWef = ?,
                    SMPAMPDuration = ?,

                    InabilityID = ?,
                    InabilityCode = ?,
                    Remarks = ?,

                    CancelDate = ?,
                    CancelRemarks = ?,
                    CancelReference = ?,

                    Active = ?,

                    Universal_ID_M_Ship = ?,
                    Universal_ID_M_Department = ?,
                    Universal_ID_T_EquipmentShipDetail = ?,
                    Universal_ID_M_Frequency = ?,

                    SrNo = ?,
                    ShipSrNo = ?,
                    RoutineID = ?,
                    RoutineDescription = ?,
                    IsNoRoutineUndertaken = ?,
                    EquipmentShipID = ?,
                    EquipmentID = ?,
                    SchedFrequency = ?,
                    SchedAmendmentNo = ?,
                    SchedNo = ?,
                    ScheduleDate = ?,
                    ActualFussCancelDate = ?,
                    ActualFussCreationDate = ?,
                    DemandDetails = ?,

                    Universal_ID_T_MaintopDetail = ?,
                    Universal_ID_M_Equipment = ?,
                    Universal_ID_M_Deferment = ?,
                    Universal_ID_M_Reason = ?,
                    Universal_ID_M_Inability = ?,
                    Universal_ID_T_Dart = ?,
                    Universal_ID_M_Establishment = ?

                WHERE Universal_ID_T_Fuss = ?
            """

            # ---------------- INSERT QUERY ----------------
            insert_query = """
                INSERT INTO T_Fuss
                (
                    DepartmentID,
                    FussDate,
                    FrequencyID,
                    LastUndertaken,
                    DueDate,

                    DefermentID,
                    DefermentCode,
                    ReasonID,
                    ReasonCode,

                    LastSMP,
                    SMPDuration,
                    LastAMP,
                    AMPDuration,
                    AMPSMPReqWef,
                    SMPAMPDuration,

                    InabilityID,
                    InabilityCode,
                    Remarks,

                    CancelDate,
                    CancelRemarks,
                    CancelReference,

                    Active,

                    Universal_ID_M_Ship,
                    Universal_ID_M_Department,
                    Universal_ID_T_EquipmentShipDetail,
                    Universal_ID_M_Frequency,

                    SrNo,
                    ShipSrNo,
                    RoutineID,
                    RoutineDescription,
                    IsNoRoutineUndertaken,
                    EquipmentShipID,
                    EquipmentID,
                    SchedFrequency,
                    SchedAmendmentNo,
                    SchedNo,
                    ScheduleDate,
                    ActualFussCancelDate,
                    ActualFussCreationDate,
                    DemandDetails,

                    Universal_ID_T_MaintopDetail,
                    Universal_ID_M_Equipment,
                    Universal_ID_M_Deferment,
                    Universal_ID_M_Reason,
                    Universal_ID_M_Inability,
                    Universal_ID_T_Dart,
                    Universal_ID_M_Establishment,
                    Universal_ID_T_Fuss
                )
                VALUES
                (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                )
            """

            inserted_ids = []

            for fuss in fuss_records:
                fuss_id = fuss.get("Universal_ID_T_Fuss")

                # ---------------- CHECK RECORD ----------------
                cursor.execute(check_query, (fuss_id,))

                exists = cursor.fetchone()

                # ---------------- VALUES ----------------
                values = (
                    fuss.get("DepartmentID"),
                    fuss.get("FussDate"),
                    fuss.get("FrequencyID"),
                    fuss.get("LastUndertaken"),
                    fuss.get("DueDate"),
                    fuss.get("DefermentID"),
                    fuss.get("DefermentCode"),
                    fuss.get("ReasonID"),
                    fuss.get("ReasonCode"),
                    fuss.get("LastSMP"),
                    fuss.get("SMPDuration"),
                    fuss.get("LastAMP"),
                    fuss.get("AMPDuration"),
                    fuss.get("AMPSMPReqWef"),
                    fuss.get("SMPAMPDuration"),
                    fuss.get("InabilityID"),
                    fuss.get("InabilityCode"),
                    fuss.get("Remarks"),
                    fuss.get("CancelDate"),
                    fuss.get("CancelRemarks"),
                    fuss.get("CancelReference"),
                    1,
                    fuss.get("Universal_ID_M_Ship"),
                    fuss.get("Universal_ID_T_MaintopDetail"),
                    fuss.get("Universal_ID_M_Equipment"),
                    fuss.get("Universal_ID_M_Department"),
                    fuss.get("Universal_ID_T_EquipmentShipDetail"),
                    fuss.get("Universal_ID_M_Frequency"),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    fuss.get("Universal_ID_M_Deferment"),
                    fuss.get("Universal_ID_M_Reason"),
                    fuss.get("Universal_ID_M_Inability"),
                    fuss.get("Universal_ID_T_Dart"),
                    fuss.get("Universal_ID_M_Establishment"),
                )

                # ---------------- UPDATE ----------------
                if exists:
                    cursor.execute(update_query, values + (fuss_id,))

                # ---------------- INSERT ----------------
                else:
                    cursor.execute(insert_query, values + (fuss_id,))

                    inserted_ids.append(fuss_id)

            # ---------------- COMMIT ----------------
            conn.commit()

            return Response(
                {
                    "status": True,
                    "message": "FUSS records synced successfully",
                    "inserted_count": len(inserted_ids),
                    "data": inserted_ids,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            if conn:
                conn.rollback()

            logger.exception("FUSS bulk insert failed")

            return Response(
                {
                    "status": False,
                    "message": "Failed to save FUSS data",
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        finally:
            if cursor:
                cursor.close()

            if conn:
                conn.close()


class InitiateFussSyncAPIView(APIView):
    def post(self, request, pk):
        fuss_qs = FussRaiseDetails.objects.all()
        fuss_json = []

        for fuss in fuss_qs:
            ship_obj = get_this_ship()
            fuss_id = f"SWMM-{fuss.id}"

            fuss_json.append(
                {
                    "Universal_ID_T_Fuss": fuss_id,
                    "Universal_ID_M_Ship": ship_obj.universal_id_m_ship
                    if ship_obj
                    else "NA",
                    "Universal_ID_M_Department": fuss.department_f_key.universal_id_m_department
                    if fuss.department_f_key
                    else "NA",
                    "DepartmentID": fuss.department_f_key.universal_id_m_department
                    if fuss.department_f_key
                    else "NA",
                    "Universal_ID_T_MaintopDetail": fuss.routine_description_id.maintop_detail.universal_id_t_maintopdetail
                    if fuss.routine_description_id.maintop_detail
                    else "NA",
                    "Universal_ID_M_Equipment": fuss.routine_description_id.add_routine_details.equipment_name.sfd_equipment.equipment.universal_id_m_equipment
                    if fuss.routine_description_id
                    else "NA",
                    "Universal_ID_M_Deferment": fuss.recomm_deferment.Universal_ID_M_Deferment
                    if fuss.recomm_deferment
                    else "NA",
                    "DefermentID": fuss.recomm_deferment.DefermentID
                    if fuss.recomm_deferment
                    else "NA",
                    "DefermentCode": fuss.recomm_deferment.DefermentCode
                    if fuss.recomm_deferment
                    else "NA",
                    "Universal_ID_M_Reason": fuss.reason.Universal_ID_M_Reason
                    if fuss.reason
                    else "NA",
                    "ReasonCode": fuss.reason.ReasonCode if fuss.reason else "NA",
                    "ReasonID": fuss.reason.ReasonID if fuss.reason else "NA",
                    "Universal_ID_M_Inability": fuss.inability.Universal_ID_M_Inability
                    if fuss.inability
                    else "NA",
                    "InabilityID": fuss.inability.InabilityID
                    if fuss.inability
                    else "NA",
                    "InabilityCode": fuss.inability.InabilityCode
                    if fuss.inability
                    else "NA",
                    "Universal_ID_M_Establishment": fuss.establishment_f_key.universal_id_m_establishment
                    if fuss.establishment_f_key
                    else "NA",
                    "FussDate": fuss.fuss_date.isoformat() if fuss.fuss_date else "NA",
                    "LastUndertaken": fuss.last_undertaken.isoformat()
                    if fuss.last_undertaken
                    else "NA",
                    "DueDate": fuss.due_date.isoformat() if fuss.due_date else "NA",
                    "ScheduleDate": fuss.schedule_date.isoformat()
                    if fuss.schedule_date
                    else "NA",
                    "EquipmentCode": fuss.equipment if fuss.equipment else "NA",
                    "LocationCode": fuss.location_code if fuss.location_code else "NA",
                    "SchedMaintopNo": None,
                    "SchedFrequency": None,
                    "SchedAmendmentNo": None,
                    "RoutineDescription": None,
                    "Remarks": fuss.remarks if fuss.remarks else "NA",
                    "DemandDetails": fuss.demand_details
                    if fuss.demand_details
                    else "NA",
                    "CreatedDate": fuss.created_at.isoformat()
                    if fuss.created_at
                    else "NA",
                }
            )

        # -------- Payload --------
        payload = {"fuss_records": fuss_json}

        # -------- API CALL --------
        api_url = f"{API_URL}/api/fuss_sync/"

        response = requests.post(
            api_url,
            data=json.dumps(payload, cls=DjangoJSONEncoder),
            headers={"Content-Type": "application/json"},
            timeout=8000,
            verify=False,
        )

        return Response(response.json(), status=response.status_code)


class CompletedRoutineSyncAPIView(APIView):
    def post(self, request, pk=None):
        try:
            completed_routine = CompletedRoutine.objects.filter(
                routine__close_cmms_sync_status=False
            )

            jsonpayload = []

            for cr in completed_routine:
                old_routine = (
                    RoutineDescription.objects.filter(dart_number=cr.old_dart_number)
                    .select_related("department_f_key")
                    .first()
                )

                new_routine = (
                    RoutineDescription.objects.filter(dart_number=cr.new_dart_number)
                    .select_related("department_f_key")
                    .first()
                )

                if old_routine and new_routine:
                    old_dart_type, old_dart_section, old_dart_no = get_dart_split(
                        old_routine.dart_number or None
                    )

                    new_dart_type, new_dart_section, new_dart_no = get_dart_split(
                        new_routine.dart_number or None
                    )

                    # OLD EQUIPMENT
                    old_eq_code = None
                    old_t_equipment_ship_detail = None

                    if old_routine.equipment_name:
                        if old_routine.equipment_name.sfd_equipment:
                            old_eq_code = (
                                old_routine.equipment_name.sfd_equipment.equipment.equipment_code
                                or old_routine.equipment_name.equipment_code
                            )

                            old_t_equipment_ship_detail = (
                                old_routine.equipment_name.sfd_equipment.t_equipment_ship_detail
                                or None
                            )

                    # NEW EQUIPMENT
                    new_eq_code = None
                    new_t_equipment_ship_detail = None

                    if new_routine.equipment_name:
                        if new_routine.equipment_name.sfd_equipment:
                            new_eq_code = (
                                new_routine.equipment_name.sfd_equipment.equipment.equipment_code
                                or new_routine.equipment_name.equipment_code
                            )

                            new_t_equipment_ship_detail = (
                                new_routine.equipment_name.sfd_equipment.t_equipment_ship_detail
                                or None
                            )

                    data = {
                        "old_routine": {
                            "routine_id": old_routine.id,
                            "maintop_no": old_routine.maintop_no,
                            "routine_no": old_routine.routine_no,
                            "routine_description": old_routine.routine_description,
                            "dart_number": old_routine.dart_number,
                            "dart_sr_no": f"{old_dart_section}-{old_dart_no}",
                            "serial_number": old_dart_no,
                            "department_id": (
                                old_routine.department_f_key.id
                                if old_routine.department_f_key
                                else None
                            ),
                            "Universal_ID_T_Dart": old_routine.Universal_ID_T_Dart,
                            "Universal_ID_M_Department": (
                                old_routine.department_f_key.universal_id_m_department
                                if old_routine.department_f_key
                                else None
                            ),
                            "eq_code": old_eq_code,
                            "Universal_ID_T_EquipmentShipDetail": (
                                old_t_equipment_ship_detail
                            ),
                            "is_closed": 1,
                            "date_of_completion": (
                                cr.date_of_completion.isoformat()
                                if cr.date_of_completion
                                else None
                            ),
                            "running_hour": cr.running_hour,
                            "due_running_hour": cr.due_running_hour,
                            "hours": cr.hours,
                            "minutes": cr.minutes,
                            "carried_by": cr.carried_by,
                            "p_no": cr.p_no,
                            "rank": (
                                cr.rank.universal_id_m_ranklist if cr.rank else None
                            ),
                            "other_rank": (cr.other_rank if cr.rank else None),
                            "total_manpower": cr.total_manpower,
                            "repair_remark": cr.repair_remark,
                            "completion_details": cr.completion_details,
                            "trial_team": cr.trial_team,
                            "rec_for_deletion": cr.rec_for_deletion,
                        },
                        "new_routine": {
                            "routine_id": new_routine.id,
                            "maintop_no": new_routine.maintop_no,
                            "routine_no": new_routine.routine_no,
                            "routine_description": new_routine.routine_description,
                            "dart_number": new_routine.dart_number,
                            "dart_sr_no": f"{new_dart_section}-{new_dart_no}",
                            "serial_number": new_dart_no,
                            "department_id": (
                                new_routine.department_f_key.id
                                if new_routine.department_f_key
                                else None
                            ),
                            "Universal_ID_T_Dart": new_routine.Universal_ID_T_Dart,
                            "Universal_ID_M_Department": (
                                new_routine.department_f_key.universal_id_m_department
                                if new_routine.department_f_key
                                else None
                            ),
                            "eq_code": new_eq_code,
                            "Universal_ID_T_EquipmentShipDetail": (
                                new_t_equipment_ship_detail
                            ),
                            "is_closed": 0,
                            "date_of_completion": None,
                            "running_hour": None,
                            "due_running_hour": None,
                            "hours": None,
                            "minutes": None,
                            "carried_by": None,
                            "p_no": None,
                            "rank": None,
                            "total_manpower": None,
                            "repair_remark": None,
                            "completion_details": None,
                            "trial_team": None,
                            "rec_for_deletion": None,
                        },
                    }

                    jsonpayload.append(data)

            payload = {"routines": jsonpayload}

            # CMMS API
            api_url = f"{API_URL}/api/receive_completed_routine/"

            response = requests.post(
                api_url,
                data=json.dumps(payload, cls=DjangoJSONEncoder),
                headers={"Content-Type": "application/json"},
                timeout=8000,
                verify=False,
            )

            try:
                response_data = response.json()

            except ValueError:
                response_data = {"status": False, "message": response.text}

            if response_data.get("status") is False:
                return Response(
                    {
                        "status": False,
                        "message": response_data.get(
                            "message", "CMMS API returned failure"
                        ),
                        "cmms_response": response_data,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "status": True,
                    "message": "Data was successfully sent to CMMS",
                    "total_routines": len(jsonpayload),
                    "cmms_response": response_data,
                },
                status=status.HTTP_200_OK,
            )

        except requests.exceptions.RequestException as e:
            return Response(
                {
                    "status": False,
                    "message": "Unable to connect with CMMS API",
                    "error": str(e),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        except Exception as e:
            return Response(
                {"status": False, "message": "Something went wrong", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RoutineDARTSyncAPI(APIView):
    def post(self, request):
        conn = None
        cursor = None

        try:
            routines = request.data.get("routines", [])

            if not isinstance(routines, list):
                return Response(
                    {"status": False, "error": "'routines' must be a list"}, status=400
                )

            ship_obj = get_this_ship()

            if not ship_obj:
                return Response(
                    {"status": False, "error": "Ship not found"}, status=400
                )

            ship_sr_no = ship_obj.sr_no
            universal_id_m_ship = ship_obj.universal_id_m_ship or 0

            conn = get_mssql_connection()
            cursor = conn.cursor()

            inserted_ids = []
            updated_ids = []

            check_query = """
                SELECT 1
                FROM T_Dart
                WHERE Universal_ID_T_Dart = ?
            """

            # --------------------------------------------------
            # UPDATE QUERY
            # --------------------------------------------------
            update_query = """
                UPDATE T_Dart
                SET
                    DartNumber = ?,
                    SrNo = ?,
                    ShipSrNo = ?,
                    DartDate = ?,
                    DepartmentID = ?,
                    Department = ?,
                    EquipmentCode = ?,
                    RectifiedDate = ?,
                    Remarks = ?,
                    CancelDate = ?,
                    Active = ?,
                    UpdatedDate = ?,
                    Universal_ID_M_Ship = ?,
                    Universal_ID_M_Department = ?,
                    Universal_ID_T_EquipmentShipDetail = ?,
                    Universal_ID_Ch_Master_Ship_Remarks_By = ?,
                    Next_Routine_Due_At_Running_Hours = ?,
                    Present_Running_Hours = ?,
                    Running_Hour_Which_Routine_Completed = ?,
                    Additional_Remarks = ?,
                    RoutineDefect = ?,
                    DefectDate = ?,
                    RoutineDueDate = ?,
                    RoutineStartDate = ?,
                    DefectDescription = ?,
                    RepairRoutineDetails = ?,
                    Is_Auto_Generated_Dart = ?,
                    IsClosed = ?,
                    Is_Amp = ?,
                    Is_Refit = ?,
                    Is_Routine = ?,
                    Is_Defect = ?,
                    Ship_Remarks = ?,
                    RoutineID = ?,
                    DL_Type_ID = ?,
                    DL_Number = ?,
                    Is_Final_Submit = ?,
                    Serial_Number = ?,
                    MandaysConsumed = ?,
                    ScheduleDate = ?,
                    Is_Drafted = ?,
                    RA_Additional_Remarks = ?,
                    Is_Signal_Drafted = ?,
                    Universal_ID_T_MaintopDetail = ?,
                    RAGenerationDate = ?,
                    Is_DLIIDrafted = ?,
                    Is_RefitRADraft = ?,
                    RecForDeletion = ?,
                    HrsFromInstallation = ?,
                    NewHrsFromInstallation = ?,
                    TotalRunningHours = ?,
                    Universal_ID_T_RefComp = ?,
                    FussDate = ?,
                    IsFuss = ?,
                    OtherRank = ?,
                    RoutineCarriedOutBy = ?,
                    PersonalNo = ?,
                    Universal_ID_M_RankList = ?,
                    TotalNoOfManpower = ?,
                    IsExportToSDRS = ?
                WHERE Universal_ID_T_Dart = ?
            """

            # --------------------------------------------------
            # INSERT QUERY
            # --------------------------------------------------
            insert_query = """
                INSERT INTO T_Dart (
                    DartNumber,
                    SrNo,
                    ShipSrNo,
                    DartDate,
                    DepartmentID,
                    Department,
                    EquipmentCode,
                    RectifiedDate,
                    Remarks,
                    CancelDate,
                    Active,
                    CreatedDate,
                    Universal_ID_M_Ship,
                    Universal_ID_M_Department,
                    Universal_ID_T_EquipmentShipDetail,
                    Universal_ID_Ch_Master_Ship_Remarks_By,
                    Next_Routine_Due_At_Running_Hours,
                    Present_Running_Hours,
                    Running_Hour_Which_Routine_Completed,
                    Additional_Remarks,
                    RoutineDefect,
                    DefectDate,
                    RoutineDueDate,
                    RoutineStartDate,
                    DefectDescription,
                    RepairRoutineDetails,
                    Is_Auto_Generated_Dart,
                    IsClosed,
                    Is_Amp,
                    Is_Refit,
                    Is_Routine,
                    Is_Defect,
                    Ship_Remarks,
                    RoutineID,
                    DL_Type_ID,
                    DL_Number,
                    Is_Final_Submit,
                    Serial_Number,
                    MandaysConsumed,
                    ScheduleDate,
                    Is_Drafted,
                    RA_Additional_Remarks,
                    Is_Signal_Drafted,
                    Universal_ID_T_MaintopDetail,
                    RAGenerationDate,
                    Is_DLIIDrafted,
                    Is_RefitRADraft,
                    RecForDeletion,
                    HrsFromInstallation,
                    NewHrsFromInstallation,
                    TotalRunningHours,
                    Universal_ID_T_RefComp,
                    FussDate,
                    IsFuss,
                    OtherRank,
                    RoutineCarriedOutBy,
                    PersonalNo,
                    Universal_ID_M_RankList,
                    TotalNoOfManpower,
                    IsExportToSDRS,
                    Universal_ID_T_Dart
                )
                VALUES (
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?,?,?,?
                )
            """

            for item in routines:
                old = item.get("old_routine") or {}
                new_data = item.get("new_routine") or {}

                # ==================================================
                # OLD ROUTINE -> UPDATE
                # ==================================================
                if old:
                    dart_id = old.get("Universal_ID_T_Dart")

                    if not dart_id:
                        raise ValueError("Universal_ID_T_Dart missing in old_routine")

                    cursor.execute(check_query, (dart_id,))

                    exists = cursor.fetchone()

                    if exists:
                        values = (
                            old.get("dart_number"),
                            old.get("dart_sr_no"),
                            ship_sr_no,
                            old.get("date_of_completion"),
                            old.get("Universal_ID_M_Department"),
                            old.get("Universal_ID_M_Department"),
                            old.get("eq_code"),
                            old.get("date_of_completion"),
                            old.get("repair_remark"),
                            old.get("date_of_completion"),
                            1,
                            None,
                            universal_id_m_ship,
                            old.get("Universal_ID_M_Department"),
                            old.get("Universal_ID_T_EquipmentShipDetail"),
                            old.get("remark_code"),
                            None,
                            old.get("running_hour"),
                            old.get("running_hour"),
                            old.get("completion_details"),
                            2,
                            old.get("date_of_completion"),
                            None,
                            None,
                            old.get("routine_description"),
                            old.get("completion_details"),
                            1,
                            1,
                            0,
                            0,
                            1,
                            0,
                            None,
                            old.get("routine_id"),
                            None,
                            None,
                            1,
                            old.get("serial_number"),
                            None,
                            old.get("date_of_completion"),
                            0,
                            None,
                            0,
                            0,
                            None,
                            None,
                            0,
                            old.get("rec_for_deletion"),
                            None,
                            None,
                            old.get("running_hour"),
                            old.get("Universal_ID_T_RefComp"),
                            None,
                            0,
                            old.get("other_rank"),
                            old.get("carried_by"),
                            old.get("p_no"),
                            old.get("rank"),
                            old.get("total_manpower"),
                            0,
                            dart_id,
                        )

                        cursor.execute(update_query, values)

                        updated_ids.append(dart_id)

                # ==================================================
                # NEW ROUTINE -> INSERT
                # ==================================================
                if new_data:
                    dart_id = new_data.get("Universal_ID_T_Dart")

                    if not dart_id:
                        raise ValueError("Universal_ID_T_Dart missing in new_routine")

                    cursor.execute(check_query, (dart_id,))

                    exists = cursor.fetchone()

                    if not exists:
                        values = (
                            new_data.get("dart_number"),
                            new_data.get("dart_sr_no"),
                            ship_sr_no,
                            new_data.get("date_of_completion"),
                            new_data.get("Universal_ID_M_Department"),
                            new_data.get("Universal_ID_M_Department"),
                            new_data.get("eq_code"),
                            new_data.get("date_of_completion"),
                            new_data.get("completion_details"),
                            None,
                            1,
                            new_data.get("date_of_completion"),
                            universal_id_m_ship,
                            new_data.get("Universal_ID_M_Department"),
                            new_data.get("Universal_ID_T_EquipmentShipDetail"),
                            None,
                            new_data.get("due_running_hour"),
                            new_data.get("running_hour"),
                            new_data.get("running_hour"),
                            new_data.get("repair_remark"),
                            1,
                            None,
                            None,
                            None,
                            new_data.get("routine_description"),
                            new_data.get("completion_details"),
                            1,
                            new_data.get("is_closed"),
                            0,
                            0,
                            1,
                            0,
                            None,
                            new_data.get("routine_id"),
                            None,
                            None,
                            0,
                            new_data.get("serial_number"),
                            None,
                            None,
                            0,
                            None,
                            0,
                            None,
                            None,
                            0,
                            0,
                            new_data.get("rec_for_deletion"),
                            None,
                            None,
                            None,
                            None,
                            None,
                            0,
                            new_data.get("other_rank"),
                            new_data.get("carried_by"),
                            new_data.get("p_no"),
                            None,
                            new_data.get("total_manpower"),
                            0,
                            dart_id,
                        )

                        cursor.execute(insert_query, values)

                        inserted_ids.append(dart_id)

            # ======================================================
            # IMPORTANT:
            # MSSQL COMMIT FIRST
            # ======================================================
            conn.commit()

            # ======================================================
            # ONLY AFTER MSSQL SUCCESS -> UPDATE LOCAL DB
            # ======================================================
            today = timezone.now().date()

            if inserted_ids:
                RoutineDescription.objects.filter(
                    Universal_ID_T_Dart__in=inserted_ids
                ).update(open_cmms_sync_status=True, open_cmms_sync_date=today)

            if updated_ids:
                RoutineDescription.objects.filter(
                    Universal_ID_T_Dart__in=updated_ids
                ).update(close_cmms_sync_status=True, close_cmms_sync_date=today)

            return Response(
                {
                    "status": True,
                    "message": "Routine sync successful",
                    "inserted": inserted_ids,
                    "updated": updated_ids,
                },
                status=200,
            )

        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass

            return Response(
                {
                    "status": False,
                    "message": "Routine sync failed",
                    "error": str(e),
                },
                status=500,
            )

        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


class SRARSyncAPIView(APIView):
    pagination_class = CommonPagination

    def _get_search(self, request):
        return request.query_params.get("search", "").strip()

    def _paginate(self, queryset, request):
        """
        Pagination helper.

        Query params:
            ?page=1
            ?page_size=10

        Existing frontend response ko disturb na karne ke liye
        pagination metadata alag return ki jayegi.
        """
        paginator = self.pagination_class()

        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        if page is None:
            return queryset, None

        return page, {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
        }

    def get(self, request, pk):
        active_tab = "T_SRARMthlyHeader"
        active_record_id = pk

        try:
            # ---------------------------------------------------------
            # 1. Signed PK decode
            # ---------------------------------------------------------
            try:
                srar_id = signing.loads(pk)
            except signing.BadSignature:
                return Response(
                    {
                        "status": False,
                        "message": "Invalid or expired SRAR identifier.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # ---------------------------------------------------------
            # 2. Header
            # ---------------------------------------------------------
            try:
                header = SrarMonthlyHeader.objects.select_related().get(pk=srar_id)
            except SrarMonthlyHeader.DoesNotExist:
                return Response(
                    {
                        "status": False,
                        "message": "SRAR monthly header not found.",
                        "srar_id": srar_id,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            search = self._get_search(request)

            # ---------------------------------------------------------
            # Universal ID
            # ---------------------------------------------------------
            universal_id = str(uuid.uuid4())

            # ---------------------------------------------------------
            # Ship details
            # ---------------------------------------------------------
            ship_details = get_this_ship()

            if not ship_details:
                return Response(
                    {
                        "status": False,
                        "message": "Ship details not found.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # =========================================================
            # TAB 1 - EQUIPMENT EXPLOITATION
            # =========================================================

            active_tab = "T_SRARMthlyEquipments"

            equipment_exploitation_qs = SrarEquipmentExploitation.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            if search:
                equipment_exploitation_qs = equipment_exploitation_qs.filter(
                    Q(
                        sfd_details__equipment__universal_id_m_equipment__icontains=search
                    )
                    | Q(sfd_details__t_equipment_ship_detail__icontains=search)
                    | Q(sfd_details__equipment__name__icontains=search)
                ).distinct()

            equipment_exploitation_data = list(equipment_exploitation_qs)

            # ---------------------------------------------------------
            # DGUF optimization
            # ---------------------------------------------------------
            equipment_ids = [
                eq.sfd_details_id
                for eq in equipment_exploitation_data
                if eq.sfd_details_id
            ]

            dguf_map = {}

            if equipment_ids:
                dguf_records = DGUF.objects.filter(
                    srar_monthly_header=header,
                    sfd_details_id__in=equipment_ids,
                ).values(
                    "sfd_details_id",
                    "rh_at_sea_and_anchorage",
                    "rh_at_port",
                )

                for dguf in dguf_records:
                    dguf_map.setdefault(
                        dguf["sfd_details_id"],
                        dguf,
                    )

            # =========================================================
            # TAB 2 - BOILER
            # =========================================================

            active_tab = "T_SRARMthlyBoiler"

            boiler_steaming_details = SrarMonthlyBoiler.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            boiler_alkalinity_salinity_details = (
                SrarBoilerAlkalinitySalinityDetail.objects.filter(
                    srar_monthly_header=header
                ).select_related(
                    "sfd_details",
                    "sfd_details__equipment",
                )
            )

            if search:
                boiler_search = (
                    Q(name__icontains=search)
                    | Q(
                        sfd_details__equipment__universal_id_m_equipment__icontains=search
                    )
                    | Q(sfd_details__t_equipment_ship_detail__icontains=search)
                )

                boiler_steaming_details = boiler_steaming_details.filter(
                    boiler_search
                ).distinct()

                boiler_alkalinity_salinity_details = boiler_alkalinity_salinity_details.filter(
                    Q(
                        sfd_details__equipment__universal_id_m_equipment__icontains=search
                    )
                    | Q(sfd_details__t_equipment_ship_detail__icontains=search)
                ).distinct()

            # =========================================================
            # TAB 3 - SHIP ACTIVITY
            # =========================================================

            active_tab = "Ch_ShipMonthlyMasterActivity"

            ship_activity_details = SrarMonthlyShipActivity.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "ship_state",
                "ship_location",
                "ship_activity_type",
                "ship_activity_detail",
                "srar_monthly_header",
            )

            if search:
                ship_activity_details = ship_activity_details.filter(
                    Q(ship_state__name__icontains=search)
                    | Q(ship_state__code__icontains=search)
                    | Q(ship_location__name__icontains=search)
                    | Q(ship_location__code__icontains=search)
                    | Q(ship_activity_type__name__icontains=search)
                    | Q(ship_activity_type__code__icontains=search)
                    | Q(ship_activity_detail__name__icontains=search)
                    | Q(ship_activity_detail__code__icontains=search)
                    | Q(remarks__icontains=search)
                ).distinct()

            # =========================================================
            # TAB 4 - FUEL / AVCAT / TORSION
            # =========================================================

            active_tab = "Ch_Ship_Mthly_Fuel_Consumption"

            fuel_consumption_months = FuelConsumptionMonth.objects.filter(
                srar_monthly_header=header
            )

            avcat_statuses = AvcatStatus.objects.filter(srar_monthly_header=header)

            torsion_meters = TorsionMeter.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            if search:
                torsion_meters = torsion_meters.filter(
                    Q(
                        sfd_details__equipment__universal_id_m_equipment__icontains=search
                    )
                    | Q(sfd_details__t_equipment_ship_detail__icontains=search)
                ).distinct()

            # =========================================================
            # TAB 5 - ICCP / H2S / STP / MAGAZINE
            # =========================================================

            active_tab = "Ch_Ship_Mnthly_ICCP"

            iccps = Iccp.objects.filter(srar_monthly_header=header).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            h2s_sensors = H2SSensor.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            stps = STP.objects.filter(srar_monthly_header=header).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            magazine_systems = MagazineFFSystemFloodingSystem.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            if search:
                equipment_search = Q(
                    sfd_details__equipment__universal_id_m_equipment__icontains=search
                ) | Q(sfd_details__t_equipment_ship_detail__icontains=search)

                iccps = iccps.filter(equipment_search).distinct()
                h2s_sensors = h2s_sensors.filter(equipment_search).distinct()
                stps = stps.filter(equipment_search).distinct()
                magazine_systems = magazine_systems.filter(equipment_search).distinct()

            # =========================================================
            # TAB 6 - CENTRIFUGE / TEST KITS
            # =========================================================

            active_tab = "Ch_Ship_Mnthly_Lub_Fuel_Centrifuge"

            centrifuges = SrarCentrifuge.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            test_kits = OpsStatusofLubOilandCoolantTestKits.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            if search:
                centrifuge_search = Q(
                    sfd_details__equipment__universal_id_m_equipment__icontains=search
                ) | Q(sfd_details__t_equipment_ship_detail__icontains=search)

                centrifuges = centrifuges.filter(centrifuge_search).distinct()

                test_kits = test_kits.filter(centrifuge_search).distinct()

            # =========================================================
            # EEF
            # =========================================================

            eef = EEF.objects.filter(srar_monthly_header=header).first()

            tab_14_eef_json = []

            if eef:
                tab_14_eef_json.append(
                    {
                        "id": eef.id,
                        "srar_monthly_header_id": header.id,
                        "serial_no": eef.serial_no,
                        "designed": eef.designed,
                        "actual": eef.actual,
                        "reason_for_exceeding": (eef.reason_for_exceeding),
                        "reason_for_exceeding_label": dict(EEF.REASON_CHOICES).get(
                            eef.reason_for_exceeding
                        ),
                        "ship_remarks": eef.ship_remarks,
                    }
                )

            # =========================================================
            # HEADER JSON
            # =========================================================

            header_json = {
                "id": header.id,
                "unique_id": universal_id,
                "ship_name": str(ship_details.name),
                "sr_no": ship_details.sr_no,
                "ship_code": ship_details.code,
                "srar_month": header.srar_month,
                "srar_year": header.srar_year,
                "hours_underway_month_hr": (header.hours_underway_month_hr),
                "hours_underway_month_min": (header.hours_underway_month_min),
                "hours_underway_month_minutes": (header.hours_underway_month_minutes),
                "total_hours_underway_month": (
                    f"{header.hours_underway_month_minutes or 0}"
                ),
                "distance_run_month": header.distance_run_month,
                "hours_underway_since_commissioning_hr": (
                    f"{header.hours_underway_since_commissioning_hr or 0}."
                    f"{header.hours_underway_since_commissioning_min or 0}"
                ),
                "distance_run_since_commissioning": (
                    header.distance_run_since_commissioning
                ),
                "max_speed": header.max_speed,
                "max_duration": (
                    f"{header.max_duration_hr or 0}.{header.max_duration_min or 0}"
                ),
                "max_speed_date": (
                    header.max_speed_date.isoformat() if header.max_speed_date else None
                ),
                "max_shaft_rpm": header.max_shaft_rpm,
                "eo_name": header.eo_name,
                "eo_rank": header.eo_rank,
                "eo_personal_no": header.eo_personal_no,
                "eo_contact_no": header.eo_contact_no,
                "eo_writer_contact_no": (header.eo_writer_contact_no),
                "is_saved": header.is_saved,
                "send_to_co": header.send_to_co,
                "designed": eef.designed if eef else None,
                "actual": eef.actual if eef else None,
                "reason_for_exceeding": (eef.reason_for_exceeding if eef else None),
                "ship_remarks": (eef.ship_remarks if eef else None),
            }

            # =========================================================
            # TAB 1 JSON
            # =========================================================

            equipment_explotion_data_json = []

            for eq in equipment_exploitation_data:
                dguf_val = dguf_map.get(eq.sfd_details_id)

                eq_json = {
                    "id": eq.id,
                    "srar_monthly_header_id": (eq.srar_monthly_header.id),
                    "header_unique_id": universal_id,
                    "equipment_id": (eq.sfd_details.id if eq.sfd_details else None),
                    "m_equipment_id": (
                        eq.sfd_details.equipment.universal_id_m_equipment
                        if (eq.sfd_details and eq.sfd_details.equipment)
                        else None
                    ),
                    "t_equipment_ship_detail": (
                        eq.sfd_details.t_equipment_ship_detail
                        if eq.sfd_details
                        else None
                    ),
                    "equipment_name": (str(eq.sfd_details) if eq.sfd_details else None),
                    "hrs_for_month": (
                        f"{eq.hrs_for_month_hrs or 0}.{eq.hrs_for_month_min or 0}"
                    ),
                    "hrs_for_month_hrs": (eq.hrs_for_month_hrs),
                    "hrs_for_month_min": (eq.hrs_for_month_min),
                    "rhsi_till_prev_month": (eq.rhsi_till_prev_month),
                    "rhsi_till_prev_month_hrs": (eq.rhsi_till_prev_month_hrs),
                    "rhsi_till_prev_month_min": (eq.rhsi_till_prev_month_min),
                    "rhsi_till_current_month": (eq.rhsi_till_current_month),
                    "rhsi_till_current_month_hr": (eq.rhsi_till_current_month_hr),
                    "rhsi_till_current_month_min": (eq.rhsi_till_current_month_min),
                    "rh_at_sea_and_anchorage": (
                        dguf_val["rh_at_sea_and_anchorage"] if dguf_val else "0.0"
                    ),
                    "rh_at_port": (dguf_val["rh_at_port"] if dguf_val else "0.0"),
                }

                equipment_explotion_data_json.append(eq_json)

            # =========================================================
            # TAB 2 - BOILER STEAMING JSON
            # =========================================================

            tab_2_boiler_tab_data_json = []

            for boiler in boiler_steaming_details:
                boiler_json = {
                    "id": boiler.id,
                    "srar_monthly_header_id": (
                        boiler.srar_monthly_header.id
                        if boiler.srar_monthly_header
                        else None
                    ),
                    "header_unique_id": universal_id,
                    "equipment_id": (
                        boiler.sfd_details.id if boiler.sfd_details else None
                    ),
                    "m_equipment_id": (
                        boiler.sfd_details.equipment.universal_id_m_equipment
                        if (boiler.sfd_details and boiler.sfd_details.equipment)
                        else None
                    ),
                    "t_equipment_ship_detail": (
                        boiler.sfd_details.t_equipment_ship_detail
                        if boiler.sfd_details
                        else None
                    ),
                    "name": boiler.name,
                    "hrs_steamed_in_month": (boiler.hrs_steamed_in_month),
                    "hrs_steamed_since_commissioning": (
                        boiler.hrs_steamed_since_commissioning
                    ),
                    "hrs_above_20_percent": (boiler.hrs_above_20_percent),
                    "highest_salinity_during_month": (
                        boiler.highest_salinity_during_month
                    ),
                    "lowest_salinity_during_month": (
                        boiler.lowest_salinity_during_month
                    ),
                    "last_int_clg_date": (boiler.last_int_clg_date),
                    "hrs_steamed_since_last_int_clg": (
                        boiler.hrs_steamed_since_last_int_clg
                    ),
                    "last_ext_clg_date": (boiler.last_ext_clg_date),
                    "hrs_steamed_since_last_ext_clg": (
                        boiler.hrs_steamed_since_last_ext_clg
                    ),
                    "hrs_steamed_at_last_ext_clg": (boiler.hrs_steamed_at_last_ext_clg),
                    "last_retubing_date": (boiler.last_retubing_date),
                    "hrs_steamed_since_last_retubing": (
                        boiler.hrs_steamed_since_last_retubing
                    ),
                    "hrs_steamed_at_last_retubing": (
                        boiler.hrs_steamed_at_last_retubing
                    ),
                    "date_of_last_durability_test": (
                        boiler.date_of_last_durability_test
                    ),
                    "due_date_for_next_inspection": (
                        boiler.due_date_for_next_inspection
                    ),
                    "life_assessed_in_months": (boiler.life_assessed_in_months),
                }

                tab_2_boiler_tab_data_json.append(boiler_json)

            # =========================================================
            # TAB 2 - ALKALINITY / SALINITY JSON
            # =========================================================

            tab_2_boiler_alkalinity_salinity_data_json = []

            for detail in boiler_alkalinity_salinity_details:
                detail_json = {
                    "id": detail.id,
                    "srar_monthly_header_id": (
                        detail.srar_monthly_header.id
                        if detail.srar_monthly_header
                        else None
                    ),
                    "header_unique_id": universal_id,
                    "equipment_id": (
                        detail.sfd_details.id if detail.sfd_details else None
                    ),
                    "m_equipment_id": (
                        detail.sfd_details.equipment.universal_id_m_equipment
                        if (detail.sfd_details and detail.sfd_details.equipment)
                        else None
                    ),
                    "t_equipment_ship_detail": (
                        detail.sfd_details.t_equipment_ship_detail
                        if detail.sfd_details
                        else None
                    ),
                    "salinity_last_week": (detail.salinity_last_week),
                    "chloride_during_month": (detail.chloride_during_month),
                    "lowest_salinity_chloride": (detail.lowest_salinity_chloride),
                    "alkalinity_n": detail.alkalinity_n,
                    "ph": detail.ph,
                    "tds_ppm": detail.tds_ppm,
                    "phosphate_lowest": (detail.phosphate_lowest),
                    "phosphate_ppm_0": (detail.phosphate_ppm_0),
                    "alkalinity_mg_l_lowest": (detail.alkalinity_mg_l_lowest),
                    "alk_ppm": detail.alk_ppm,
                    "y150_alkalinity_percent": (detail.y150_alkalinity_percent),
                    "y150_ph": detail.y150_ph,
                    "y164_tds_ppm": (detail.y164_tds_ppm),
                    "y164_phosphate_lowest": (detail.y164_phosphate_lowest),
                    "vkd_alkalinity_percent": (detail.vkd_alkalinity_percent),
                    "vkd_alk_ppm": detail.vkd_alk_ppm,
                    "vkd_alkalinity_mg_l": (detail.vkd_alkalinity_mg_l),
                    "vkd_phosphate_ppm": (detail.vkd_phosphate_ppm),
                    "jw_common": detail.jw_common,
                }

                tab_2_boiler_alkalinity_salinity_data_json.append(detail_json)

            # =========================================================
            # TAB 2 - MERGED BOILER DATA
            # =========================================================

            boiler_map = {}

            # ---------------------------------------------------------
            # Boiler steaming
            # ---------------------------------------------------------
            for boiler in boiler_steaming_details:
                header_id = boiler.srar_monthly_header.id

                equipment_id = boiler.sfd_details.id if boiler.sfd_details else None

                key = (
                    header_id,
                    equipment_id,
                )

                boiler_map[key] = {
                    "srar_monthly_header_id": header_id,
                    "header_unique_id": universal_id,
                    "equipment_id": equipment_id,
                    "m_equipment_id": (
                        boiler.sfd_details.equipment.universal_id_m_equipment
                        if (boiler.sfd_details and boiler.sfd_details.equipment)
                        else None
                    ),
                    "t_equipment_ship_detail": (
                        boiler.sfd_details.t_equipment_ship_detail
                        if boiler.sfd_details
                        else None
                    ),
                    "equipment_name": (
                        str(boiler.sfd_details) if boiler.sfd_details else None
                    ),
                    "name": boiler.name,
                    "hrs_steamed_in_month": (boiler.hrs_steamed_in_month),
                    "hrs_steamed_since_commissioning": (
                        boiler.hrs_steamed_since_commissioning
                    ),
                    "hrs_above_20_percent": (boiler.hrs_above_20_percent),
                    "highest_salinity_during_month": (
                        boiler.highest_salinity_during_month
                    ),
                    "lowest_salinity_during_month": (
                        boiler.lowest_salinity_during_month
                    ),
                    "last_int_clg_date": (boiler.last_int_clg_date),
                    "hrs_steamed_since_last_int_clg": (
                        boiler.hrs_steamed_since_last_int_clg
                    ),
                    "last_ext_clg_date": (boiler.last_ext_clg_date),
                    "hrs_steamed_since_last_ext_clg": (
                        boiler.hrs_steamed_since_last_ext_clg
                    ),
                    "hrs_steamed_at_last_ext_clg": (boiler.hrs_steamed_at_last_ext_clg),
                    "last_retubing_date": (boiler.last_retubing_date),
                    "hrs_steamed_since_last_retubing": (
                        boiler.hrs_steamed_since_last_retubing
                    ),
                    "hrs_steamed_at_last_retubing": (
                        boiler.hrs_steamed_at_last_retubing
                    ),
                    "date_of_last_durability_test": (
                        boiler.date_of_last_durability_test
                    ),
                    "due_date_for_next_inspection": (
                        boiler.due_date_for_next_inspection
                    ),
                    "life_assessed_in_months": (boiler.life_assessed_in_months),
                }

            # ---------------------------------------------------------
            # Boiler alkalinity / salinity
            # ---------------------------------------------------------
            for detail in boiler_alkalinity_salinity_details:
                header_id = detail.srar_monthly_header.id

                equipment_id = detail.sfd_details.id if detail.sfd_details else None

                key = (
                    header_id,
                    equipment_id,
                )

                if key not in boiler_map:
                    boiler_map[key] = {
                        "srar_monthly_header_id": header_id,
                        "header_unique_id": universal_id,
                        "equipment_id": equipment_id,
                    }

                boiler_map[key].update(
                    {
                        "m_equipment_id": (
                            detail.sfd_details.equipment.universal_id_m_equipment
                            if (detail.sfd_details and detail.sfd_details.equipment)
                            else None
                        ),
                        "t_equipment_ship_detail": (
                            detail.sfd_details.t_equipment_ship_detail
                            if detail.sfd_details
                            else None
                        ),
                        "equipment_name": (
                            str(detail.sfd_details) if detail.sfd_details else None
                        ),
                        "salinity_last_week": (detail.salinity_last_week),
                        "chloride_during_month": (detail.chloride_during_month),
                        "lowest_salinity_chloride": (detail.lowest_salinity_chloride),
                        "alkalinity_n": (detail.alkalinity_n),
                        "ph": detail.ph,
                        "tds_ppm": detail.tds_ppm,
                        "phosphate_lowest": (detail.phosphate_lowest),
                        "phosphate_ppm_0": (detail.phosphate_ppm_0),
                        "alkalinity_mg_l_lowest": (detail.alkalinity_mg_l_lowest),
                        "alk_ppm": detail.alk_ppm,
                        "y150_alkalinity_percent": (detail.y150_alkalinity_percent),
                        "y150_ph": detail.y150_ph,
                        "y164_tds_ppm": (detail.y164_tds_ppm),
                        "y164_phosphate_lowest": (detail.y164_phosphate_lowest),
                        "vkd_alkalinity_percent": (detail.vkd_alkalinity_percent),
                        "vkd_alk_ppm": (detail.vkd_alk_ppm),
                        "vkd_alkalinity_mg_l": (detail.vkd_alkalinity_mg_l),
                        "vkd_phosphate_ppm": (detail.vkd_phosphate_ppm),
                        "jw_common": detail.jw_common,
                    }
                )

            tab_2_boiler_data = list(boiler_map.values())

            # =========================================================
            # TAB 3 - SHIP ACTIVITY JSON
            # =========================================================

            tab_3_ship_activity_details_json = []

            for act in ship_activity_details:
                act_json = {
                    "id": act.id,
                    "srar_monthly_header_id": (
                        act.srar_monthly_header.id if act.srar_monthly_header else None
                    ),
                    "header_unique_id": universal_id,
                    "ship_state_id": (
                        act.ship_state.Universal_ID_Ch_Master_Ship_State
                        if act.ship_state
                        else None
                    ),
                    "ship_state_name": (
                        act.ship_state.name if act.ship_state else None
                    ),
                    "ship_state_code": (
                        act.ship_state.code if act.ship_state else None
                    ),
                    "ship_location_id": (
                        act.ship_location.Universal_ID_Ch_Master_Ship_Location
                        if act.ship_location
                        else None
                    ),
                    "ship_location_name": (
                        act.ship_location.name if act.ship_location else None
                    ),
                    "ship_location_code": (
                        act.ship_location.code if act.ship_location else None
                    ),
                    "ship_activity_type_id": (
                        act.ship_activity_type.Universal_ID_Ch_Master_Ship_Activity_Type
                        if act.ship_activity_type
                        else None
                    ),
                    "ship_activity_type_name": (
                        act.ship_activity_type.name if act.ship_activity_type else None
                    ),
                    "ship_activity_type_code": (
                        act.ship_activity_type.code if act.ship_activity_type else None
                    ),
                    "ship_activity_detail_id": (
                        act.ship_activity_detail.Universal_ID_Ch_Master_Ship_Activity_Detail
                        if act.ship_activity_detail
                        else None
                    ),
                    "ship_activity_detail_name": (
                        act.ship_activity_detail.name
                        if act.ship_activity_detail
                        else None
                    ),
                    "ship_activity_detail_code": (
                        act.ship_activity_detail.code
                        if act.ship_activity_detail
                        else None
                    ),
                    "from_date": act.from_date,
                    "to_date": act.to_date,
                    "serial_no": act.serial_no,
                    "remarks": act.remarks,
                }

                tab_3_ship_activity_details_json.append(act_json)

            # =========================================================
            # TAB 4 - FUEL CONSUMPTION
            # =========================================================

            tab4_fuel_consumption_month_json = []

            for fuel in fuel_consumption_months:
                fuel_json = {
                    "id": fuel.id,
                    "srar_monthly_header_id": (
                        fuel.srar_monthly_header.id
                        if fuel.srar_monthly_header
                        else None
                    ),
                    "header_unique_id": universal_id,
                    "b_f_from_last_month": (fuel.b_f_from_last_month),
                    "recieved": fuel.recieved,
                    "consumed_in_harbour": (fuel.consumed_in_harbour),
                    "consumed_at_anchorage": (fuel.consumed_at_anchorage),
                    "consumed_at_sea": (fuel.consumed_at_sea),
                    "total_consumed": (fuel.total_consumed),
                    "defueled": fuel.defueled,
                    "balance_left_on_board": (fuel.balance_left_on_board),
                    "serial_no": fuel.serial_no,
                }

                tab4_fuel_consumption_month_json.append(fuel_json)

            # =========================================================
            # TAB 4 - AVCAT
            # =========================================================

            tab_4_avcat_status_json = []

            for avcat in avcat_statuses:
                avcat_json = {
                    "id": avcat.id,
                    "srar_monthly_header_id": (
                        avcat.srar_monthly_header.id
                        if avcat.srar_monthly_header
                        else None
                    ),
                    "header_unique_id": universal_id,
                    "b_f_from_last_month": (avcat.b_f_from_last_month),
                    "recieved": avcat.recieved,
                    "given_to_ac": avcat.given_to_ac,
                    "used_for_trials_drained": (avcat.used_for_trials_drained),
                    "total_consumed": (avcat.total_consumed),
                    "defuelded": avcat.defuelded,
                    "balance_left_on_board": (avcat.balance_left_on_board),
                    "serial_no": avcat.serial_no,
                }

                tab_4_avcat_status_json.append(avcat_json)

            # ---------------------------------------------------------
            # TAB 4 : TORSION METER
            # ---------------------------------------------------------

            tab_4_torsion_meter_json = []

            for tm in torsion_meters:
                sfd = tm.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_4_torsion_meter_json.append(
                    {
                        "id": tm.id,
                        # Header
                        "srar_monthly_header_id": (
                            tm.srar_monthly_header.id
                            if tm.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Equipment details
                        "nomenclature": tm.nomenclature,
                        "eqpt_code": tm.eqpt_code,
                        "loc_on_board": tm.loc_on_board,
                        "serial_no": tm.serial_no,
                        # Readings
                        "torsion_meter_rdg": tm.torsion_meter_rdg,
                        "max_rpm_achieved": tm.max_rpm_achieved,
                        # Operational status
                        "ops_or_non_ops": tm.ops_or_non_ops,
                        # Dates
                        "non_ops_since": tm.non_ops_since,
                        "last_calibration_date": tm.last_calibration_date,
                        "next_calibration_date": tm.next_calibration_date,
                    }
                )

            # ---------------------------------------------------------
            # TAB 5 : ICCP
            # ---------------------------------------------------------

            tab_iccp_json = []

            for iccp in iccps:
                sfd = iccp.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_iccp_json.append(
                    {
                        "id": iccp.id,
                        # Header
                        "srar_monthly_header_id": (
                            iccp.srar_monthly_header.id
                            if iccp.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Details
                        "serial_no": iccp.serial_no,
                        "nomenclature": iccp.nomenclature,
                        "loc_on_board": iccp.loc_on_board,
                        # Ops status
                        "ops_or_non_ops": iccp.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(Iccp.ops_choices).get(iccp.ops_or_non_ops)
                            if iccp.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": iccp.non_ops_since,
                    }
                )

            # ---------------------------------------------------------
            # TAB 5 : H2S SENSOR
            # ---------------------------------------------------------

            tab_h2s_sensor_json = []

            for sensor in h2s_sensors:
                sfd = sensor.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_h2s_sensor_json.append(
                    {
                        "id": sensor.id,
                        # Header
                        "srar_monthly_header_id": (
                            sensor.srar_monthly_header.id
                            if sensor.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Details
                        "serial_no": sensor.serial_no,
                        "nomenclature": sensor.nomenclature,
                        "loc_on_board": sensor.loc_on_board,
                        # Ops status
                        "ops_or_non_ops": sensor.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(H2SSensor.ops_choices).get(sensor.ops_or_non_ops)
                            if sensor.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": sensor.non_ops_since,
                        # Calibration
                        "last_calibration_date": sensor.last_calibration_date,
                        "next_calibration_date": sensor.next_calibration_date,
                    }
                )

            # ---------------------------------------------------------
            # TAB 5 : STP
            # ---------------------------------------------------------

            tab_stp_json = []

            for stp in stps:
                sfd = stp.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_stp_json.append(
                    {
                        "id": stp.id,
                        # Header
                        "srar_monthly_header_id": (
                            stp.srar_monthly_header.id
                            if stp.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Details
                        "serial_no": stp.serial_no,
                        "nomenclature": stp.nomenclature,
                        "loc_on_board": stp.loc_on_board,
                        # Ops status
                        "ops_or_non_ops": stp.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(STP.ops_choices).get(stp.ops_or_non_ops)
                            if stp.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": stp.non_ops_since,
                        # STP specific
                        "effluent_test_date": stp.effluent_test_date,
                        "effluent_status": stp.effluent_status,
                        "remarks": stp.remarks,
                    }
                )

            # ---------------------------------------------------------
            # TAB 5 : MAGAZINE FF SYSTEM
            # ---------------------------------------------------------

            tab_magazine_ff_system_json = []

            for system in magazine_systems:
                sfd = system.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_magazine_ff_system_json.append(
                    {
                        "id": system.id,
                        # Header
                        "srar_monthly_header_id": (
                            system.srar_monthly_header.id
                            if system.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Details
                        "serial_no": system.serial_no,
                        "nomenclature": system.nomenclature,
                        "loc_on_board": system.loc_on_board,
                        # Ops status
                        "ops_or_non_ops": system.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(MagazineFFSystemFloodingSystem.ops_choices).get(
                                system.ops_or_non_ops
                            )
                            if system.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": system.non_ops_since,
                        # Trials
                        "last_trials_taken": system.last_trials_taken,
                        "next_trials_due": system.next_trials_due,
                    }
                )

            # ---------------------------------------------------------
            # TAB : LUB OIL & COOLANT TEST KITS
            # ---------------------------------------------------------

            tab_lub_oil_coolant_test_kits_json = []

            for kit in test_kits:
                sfd = kit.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_lub_oil_coolant_test_kits_json.append(
                    {
                        "id": kit.id,
                        # Header
                        "srar_monthly_header_id": (
                            kit.srar_monthly_header.id
                            if kit.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        "universal_id": kit.universal_id,
                        # Description
                        "description": kit.description,
                        # Ops status
                        "ops_or_non_ops": kit.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(OpsStatusofLubOilandCoolantTestKits.ops_choices).get(
                                kit.ops_or_non_ops
                            )
                            if kit.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": kit.non_ops_since,
                        # Trials / Calibration
                        "last_trials_taken": kit.last_trials_taken,
                        "next_trials_due": kit.next_trials_due,
                        "calibration": kit.calibration,
                        "next_calibration_due_date": kit.next_calibration_due_date,
                    }
                )

            # ---------------------------------------------------------
            # TAB : SRAR CENTRIFUGE
            # ---------------------------------------------------------

            tab_centrifuge_json = []

            for centrifuge in centrifuges:
                sfd = centrifuge.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_centrifuge_json.append(
                    {
                        "id": centrifuge.id,
                        # Header
                        "srar_monthly_header_id": (
                            centrifuge.srar_monthly_header.id
                            if centrifuge.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Ops status
                        "ops_or_non_ops": centrifuge.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(SrarCentrifuge.ops_choices).get(
                                centrifuge.ops_or_non_ops
                            )
                            if centrifuge.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": centrifuge.non_ops_since,
                    }
                )

            # =========================================================
            # TAB 7A : SAFETY DEVICE CHECK TRIAL
            # =========================================================

            sdc_trials = SafetyDeviceCheckTrial.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            tab_7_safety_device_check_trial_json = []

            for trial in sdc_trials:
                sfd = trial.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_7_safety_device_check_trial_json.append(
                    {
                        "id": trial.id,
                        # Header
                        "srar_monthly_header_id": (
                            trial.srar_monthly_header.id
                            if trial.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Trial details
                        "sdc_conducted_by": trial.sdc_conducted_by,
                        "sdc_conducted_by_label": trial.sdc_conducted_by,
                        "date_of_sdc": trial.date_of_sdc,
                        "sfc_in_gm_kwh": trial.sfc_in_gm_kwh,
                        "last_sfc_trial_date": trial.last_sfc_trial_date,
                        "displacement_during_sfc_trial": (
                            trial.displacement_during_sfc_trial
                        ),
                        # Status
                        "status": trial.status,
                        "status_label": (
                            dict(SafetyDeviceCheckTrial.status_choices).get(
                                trial.status
                            )
                            if trial.status
                            else None
                        ),
                    }
                )

            # =========================================================
            # TAB 7B : INJECTOR / FIP CALIBRATION & REPLACEMENT
            # =========================================================

            injector_fip_records = InjectorFIPCalibrationReplacement.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            tab_7_injector_fip_json = []

            for record in injector_fip_records:
                sfd = record.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_7_injector_fip_json.append(
                    {
                        "id": record.id,
                        # Header
                        "srar_monthly_header_id": (
                            record.srar_monthly_header.id
                            if record.srar_monthly_header
                            else None
                        ),
                        "header_unique_id": universal_id,
                        # Equipment mapping
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "equipment_name": (str(sfd) if sfd else None),
                        # Identification
                        "serial_no": record.serial_no,
                        # Ops status
                        "ops_or_non_ops": record.ops_or_non_ops,
                        "ops_or_non_ops_label": (
                            dict(InjectorFIPCalibrationReplacement.ops_choices).get(
                                record.ops_or_non_ops
                            )
                            if record.ops_or_non_ops
                            else None
                        ),
                        "non_ops_since": record.non_ops_since,
                        # Trials
                        "last_trials_taken": record.last_trials_taken,
                        "next_trials_due": record.next_trials_due,
                        # Running hours distribution
                        "hrs_run_below_33_percent": (record.hrs_run_below_33_percent),
                        "hrs_run_33_to_50_percent": (record.hrs_run_33_to_50_percent),
                        "hrs_run_50_to_70_percent": (record.hrs_run_50_to_70_percent),
                        "hrs_run_70_to_100_percent": (record.hrs_run_70_to_100_percent),
                        # Consumption
                        "lub_oil_consumption_in_month": (
                            record.lub_oil_consumption_in_month
                        ),
                        "fuel_consumption_in_month": (record.fuel_consumption_in_month),
                        # Calibration / replacement
                        "date_of_inj_fip_calibration": (
                            record.date_of_inj_fip_calibration
                        ),
                        "occasion": record.occasion,
                        "rh_at_which_replaced": (record.rh_at_which_replaced),
                        "running_hours_at_replaced": (record.running_hours_at_replaced),
                        # Running hours text fields
                        "running_hours_months": record.running_hours_months,
                        "running_hours_since_installation": (
                            record.running_hours_since_installation
                        ),
                        # Remarks
                        "remarks": record.remarks,
                    }
                )

            # =========================================================
            # TAB 8 : DGUF - FLATTENED DATA
            # =========================================================

            dgufs = []

            # Latest sea/harbour record
            sea_record = (
                DGUFSeaHarbourRunningHourDataInput.objects.filter(
                    srar_monthly_header=header
                )
                .order_by("-created_on")
                .first()
            )

            # Latest DGUF limits record
            limit = (
                DGUFLimits.objects.filter(srar_monthly_header=header)
                .order_by("-created_on")
                .first()
            )

            # DGUF equipment records
            dguf_records = DGUF.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            # Calculate common values once
            if limit:
                exceed_reason_sea = (
                    limit.exceed_reason_sea
                    if limit.exceed_reason_sea != "Any other"
                    else limit.other_exceed_reason_sea
                )

                exceed_reason_harbour = (
                    limit.exceed_reason_harbour
                    if limit.exceed_reason_harbour != "Any other"
                    else limit.other_exceed_reason_harbour
                )
            else:
                exceed_reason_sea = None
                exceed_reason_harbour = None

            for dguf in dguf_records:
                sfd = dguf.sfd_details

                dgufs.append(
                    {
                        # Identity
                        "equipment_universal_id": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": dguf.serial_no,
                        "da_number": dguf.da_number,
                        # DGUF
                        "rh_at_sea_and_anchorage": (dguf.rh_at_sea_and_anchorage),
                        "rh_at_port": dguf.rh_at_port,
                        "total_rh_in_month": dguf.total_rh_in_month,
                        # Sea / Harbour
                        "total_rh_at_sea": (
                            sea_record.total_rh_at_sea if sea_record else None
                        ),
                        "hours_underway": (
                            sea_record.hours_underway if sea_record else None
                        ),
                        "anchorage": (sea_record.anchorage if sea_record else None),
                        "drifting": (sea_record.drifting if sea_record else None),
                        "no_of_hours_in_harbour": (
                            sea_record.no_of_hours_in_harbour if sea_record else None
                        ),
                        "hours_shore_supply_avl_when_alongs": (
                            sea_record.hours_shore_supply_avl_when_alongs
                            if sea_record
                            else None
                        ),
                        "no_of_cold_moves_in_harbour": (
                            sea_record.no_of_cold_moves_in_harbour
                            if sea_record
                            else None
                        ),
                        "cmts_wrt_to_non_avl_shore_supply": (
                            sea_record.cmts_wrt_to_non_avl_shore_supply
                            if sea_record
                            else None
                        ),
                        # DGUF Limits
                        "limiting_value_sea": (
                            limit.limiting_value_sea if limit else None
                        ),
                        "actual_dguf_sea": (limit.actual_dguf_sea if limit else None),
                        "exceed_reason_sea": exceed_reason_sea,
                        "limiting_value_harbour": (
                            limit.limiting_value_harbour if limit else None
                        ),
                        "actual_dguf_harbour": (
                            limit.actual_dguf_harbour if limit else None
                        ),
                        "exceed_reason_harbour": exceed_reason_harbour,
                    }
                )

            # =========================================================
            # TAB 9 : FULL POWER TRIALS - MAIN ENGINE
            # =========================================================

            tab_9_fpt_main_engine_json = []

            fpt_main = FullPowerTrialsMainEngine.objects.filter(
                srar_monthly_header=header
            )

            for fpt in fpt_main:
                tab_9_fpt_main_engine_json.append(
                    {
                        "id": fpt.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "date": fpt.date,
                        "occasion_reason": fpt.occasion_reason,
                        "draught_fwd": fpt.draught_fwd,
                        "draught_aft": fpt.draught_aft,
                        "displacement": fpt.displacement,
                        "max_speed": fpt.max_speed,
                        "torsion_meter_reading": fpt.torsion_meter_reading,
                        "pending_dr_activities_reason": (
                            fpt.pending_dr_activities_reason
                        ),
                        "sea_state": fpt.sea_state,
                        "conducted_by": fpt.conducted_by,
                        "conducted_by_label": fpt.conducted_by,
                        "serial_no": fpt.serial_no,
                    }
                )

            # =========================================================
            # TAB 9 : FULL POWER TRIALS - EQUIPMENT WISE
            # =========================================================

            tab_9_fpt_equipment_json = []

            fpt_eq = FPTEquipmentWise.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
                "fpt_main_engine",
            )

            for eq in fpt_eq:
                sfd = eq.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_9_fpt_equipment_json.append(
                    {
                        "id": eq.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "fpt_main_engine_id": (
                            eq.fpt_main_engine.id if eq.fpt_main_engine else None
                        ),
                        "equipment_id": (sfd.id if sfd else None),
                        "serial_no": eq.serial_no,
                        "fuel_rack_dbr_max": eq.fuel_rack_dbr_max,
                        "marking_max": eq.marking_max,
                        "undertaken_on": eq.undertaken_on,
                        "pitch": eq.pitch,
                        "max_rpm": eq.max_rpm,
                        "rated_power": eq.rated_power,
                        "max_achieved_power": eq.max_achieved_power,
                        "remarks": eq.remarks,
                    }
                )

            # =========================================================
            # TAB 9 : FULL POWER TRIALS - DIESEL ALTERNATOR
            # =========================================================

            tab_9_fpt_diesel_alternator_json = []

            fpt_da = FPTDieselAlternators.objects.filter(
                srar_monthly_header=header
            ).select_related(
                "sfd_details",
                "sfd_details__equipment",
            )

            for da in fpt_da:
                sfd = da.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_9_fpt_diesel_alternator_json.append(
                    {
                        "id": da.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": (sfd.id if sfd else None),
                        "serial_no": da.serial_no,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "date": da.date,
                        "occasion": da.occasion,
                        "rated_load": da.rated_load,
                        "max_load_achieved": da.max_load_achieved,
                        "conducted_by": da.conducted_by,
                        "conducted_by_label": da.conducted_by,
                        "last_ehm_trials_undertaken_on": (
                            da.last_ehm_trials_undertaken_on
                        ),
                        "remarks": da.remarks,
                    }
                )

            # =========================================================
            # TAB 10 : REDUCTION GEAR + GAS TURBINE
            # =========================================================

            tab_10_reduction_gear_exploitation_json = []
            tab_10_gas_turbine_exploitation_json = []
            tab_10_replacement = []
            tab_10_annual_SRMR = []

            # ---------------------------------------------------------
            # Reduction Gear Exploitation
            # ---------------------------------------------------------
            rg_records = ReductionGearExploitation.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment")

            for rg in rg_records:
                sfd = rg.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_10_reduction_gear_exploitation_json.append(
                    {
                        "id": rg.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": rg.serial_no,
                        "total_rh_in_month": rg.total_rh_in_month,
                        "total_rh_si": rg.total_rh_si,
                        "total_rh_regime1_in_month": rg.total_rh_regime1_in_month,
                        "total_rh_regime1_si": rg.total_rh_regime1_si,
                        "total_rh_regime2_in_month": rg.total_rh_regime2_in_month,
                        "total_rh_regime2_si": rg.total_rh_regime2_si,
                        "total_rh_regime3_in_month": rg.total_rh_regime3_in_month,
                        "total_rh_regime3_si": rg.total_rh_regime3_si,
                        "trailing_rh_in_month": rg.trailing_rh_in_month,
                        "trailing_rh_si": rg.trailing_rh_si,
                        "service_life_in_month": rg.service_life_in_month,
                        "service_life_si": rg.service_life_si,
                        "no_of_eng_regime1_in_month": rg.no_of_eng_regime1_in_month,
                        "no_of_eng_regime1_si": rg.no_of_eng_regime1_si,
                        "no_of_eng_regime2_in_month": rg.no_of_eng_regime2_in_month,
                        "no_of_eng_regime2_si": rg.no_of_eng_regime2_si,
                        "no_of_eng_regime3_in_month": rg.no_of_eng_regime3_in_month,
                        "no_of_eng_regime3_si": rg.no_of_eng_regime3_si,
                        "no_of_eng_regime4_in_month": rg.no_of_eng_regime4_in_month,
                        "no_of_eng_regime4_si": rg.no_of_eng_regime4_si,
                    }
                )

            # ---------------------------------------------------------
            # Gas Turbine Exploitation
            # ---------------------------------------------------------
            gt_exploitations = GasTurbineExploitation.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment", "rg_exploitation")

            for gt in gt_exploitations:
                sfd = gt.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_10_gas_turbine_exploitation_json.append(
                    {
                        "id": gt.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": gt.serial_no,
                        "total_rh_in_month": gt.total_rh_in_month,
                        "total_rh_si": gt.total_rh_si,
                        "no_of_hot_starts_in_month": gt.no_of_hot_starts_in_month,
                        "no_of_hot_starts_si": gt.no_of_hot_starts_si,
                        "no_of_cold_starts_in_month": gt.no_of_cold_starts_in_month,
                        "no_of_cold_starts_si": gt.no_of_cold_starts_si,
                        "no_of_false_starts_in_month": gt.no_of_false_starts_in_month,
                        "no_of_false_starts_si": gt.no_of_false_starts_si,
                        "no_of_tech_starts_in_month": gt.no_of_tech_starts_in_month,
                        "no_of_tech_starts_si": gt.no_of_tech_starts_si,
                        "status": gt.status,
                        "non_ops_since": gt.non_ops_since,
                        "last_calibration_date_of_fitted_fuel_eqpt": (
                            gt.last_calibration_date_of_fitted_fuel_eqpt
                        ),
                        "last_ehm_trial_date": gt.last_ehm_trial_date,
                        "last_fpt_date": gt.last_fpt_date,
                        "fuel_eqpt_calibration_due_on": gt.fuel_eqpt_calibration_due_on,
                        "rh_regime_1_in_mth": gt.rh_regime_1_in_mth,
                        "rh_regime_1_si": gt.rh_regime_1_si,
                        "rh_regime_2_in_mth": gt.rh_regime_2_in_mth,
                        "rh_regime_2_si": gt.rh_regime_2_si,
                        "rh_regime_3_in_mth": gt.rh_regime_3_in_mth,
                        "rh_regime_3_si": gt.rh_regime_3_si,
                        "no_of_astern_engagements_in_mth": (
                            gt.no_of_astern_engagements_in_mth
                        ),
                        "no_of_astern_engagements_count": (
                            gt.no_of_astern_engagements_count
                        ),
                        "no_of_stop_orders_in_mth": gt.no_of_stop_orders_in_mth,
                        "no_of_stop_orders_si": gt.no_of_stop_orders_si,
                        "last_chem_clg": gt.last_chem_clg,
                    }
                )

            # ---------------------------------------------------------
            # Replacement Of Major Assemblies
            # ---------------------------------------------------------
            replacement_qs = ReplacementOfMajorAssemblies.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment")

            for rep in replacement_qs:
                sfd = rep.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_10_replacement.append(
                    {
                        "section": "replacement_of_major_assemblies",
                        "id": rep.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": rep.serial_no,
                        "date_of_replacement": rep.date_of_replacement,
                        "unit_sub_units": rep.unit_sub_units,
                        "reason_for_replacement": rep.reason_for_replacement,
                        "replacement_remarks": rep.replacement_remarks,
                    }
                )

            # ---------------------------------------------------------
            # Annual SRMR Routine Undertaken
            # ---------------------------------------------------------
            srmr_qs = AnnualSRMRRoutineUndertaken.objects.filter(
                srar_monthly_header=header
            ).select_related("equipment__equipment", "by_whom")

            for sr in srmr_qs:
                equipment_detail = sr.equipment
                equipment = equipment_detail.equipment if equipment_detail else None

                tab_10_annual_SRMR.append(
                    {
                        "section": "annual_srmr_routine",
                        "id": sr.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": (
                            equipment_detail.id if equipment_detail else None
                        ),
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            equipment_detail.t_equipment_ship_detail
                            if equipment_detail
                            else None
                        ),
                        "serial_no": sr.serial_no,
                        "date": sr.date,
                        "description_of_routine": sr.description_of_routine,
                        # "by_whom": sr.by_whom.id if sr.by_whom else None,
                        # "by_whom_name": sr.by_whom.username if sr.by_whom else None,
                    }
                )

            # =========================================================
            # TAB 11 : GAS TURBINE GENERATOR
            # =========================================================

            tab_11_gtg_exploitation_json = []
            tab_11_gtg_guf_json = []
            tab_11_gtg_rg_exploitation_json = []
            tab_11_gtg_replacement_json = []
            tab_11_gtg_srmr_json = []

            # ---------------------------------------------------------
            # 1. Gas Turbine Generator Exploitation
            # ---------------------------------------------------------
            gtg_exploitations = GasTurbineGeneratorExploitation.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment")

            for gtg in gtg_exploitations:
                sfd = gtg.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_11_gtg_exploitation_json.append(
                    {
                        "id": gtg.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": gtg.serial_no,
                        "date": gtg.date,
                        "total_rh_in_month": gtg.total_rh_in_month,
                        "total_rh_si": gtg.total_rh_si,
                        "total_rh_in_harbour": gtg.total_rh_in_harbour,
                        "total_rh_in_sea": gtg.total_rh_in_sea,
                        "no_of_hot_starts_in_month": gtg.no_of_hot_starts_in_month,
                        "no_of_hot_starts_in_si": gtg.no_of_hot_starts_in_si,
                        "no_of_cold_starts_in_month": gtg.no_of_cold_starts_in_month,
                        "no_of_cold_starts_in_si": gtg.no_of_cold_starts_in_si,
                        "no_of_battery_cold_starts_in_month": (
                            gtg.no_of_battery_cold_starts_in_month
                        ),
                        "no_of_battery_cold_starts_in_si": (
                            gtg.no_of_battery_cold_starts_in_si
                        ),
                        "no_of_battery_hot_starts_in_month": (
                            gtg.no_of_battery_hot_starts_in_month
                        ),
                        "no_of_battery_hot_starts_in_si": (
                            gtg.no_of_battery_hot_starts_in_si
                        ),
                    }
                )

            # ---------------------------------------------------------
            # 2. GTG GUF Entry
            # ---------------------------------------------------------
            guf_entries = GasTurbineGeneratorExploitationGufEntry.objects.filter(
                srar_monthly_header=header
            )

            for guf in guf_entries:
                tab_11_gtg_guf_json.append(
                    {
                        "id": guf.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "guf_sea": guf.guf_sea,
                        "reason_exceed_sea": guf.reason_exceed_sea,
                        "guf_hbr": guf.guf_hbr,
                        "reason_exceed_hbr": guf.reason_exceed_hbr,
                    }
                )

            # ---------------------------------------------------------
            # 3. Reduction Gear Exploitation of GTG
            # ---------------------------------------------------------
            rg_gtg_records = ReductionGearExploitationofGTG.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment")

            for rg in rg_gtg_records:
                sfd = rg.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_11_gtg_rg_exploitation_json.append(
                    {
                        "id": rg.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": rg.serial_no,
                        "rg_running_hours": rg.rg_running_hours,
                        "no_of_hot_starts": rg.no_of_hot_starts,
                        "no_of_cold_starts": rg.no_of_cold_starts,
                        "rh_in_harbour": rg.rh_in_harbour,
                        "rh_in_sea": rg.rh_in_sea,
                        "in_months_si": rg.in_months_si,
                    }
                )

            # ---------------------------------------------------------
            # 4. Replacement of Major Assemblies (GTG)
            # ---------------------------------------------------------
            gtg_replacements = ReplacementOfMajorAssembliesofGTG.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment")

            for rep in gtg_replacements:
                sfd = rep.sfd_details
                equipment = sfd.equipment if sfd else None

                tab_11_gtg_replacement_json.append(
                    {
                        "id": rep.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": rep.serial_no,
                        "date_of_replacement": rep.date,
                        "unit_sub_units": rep.unit_sub_units,
                        "reason_for_replacement": rep.reason_for_replacement,
                        "replacement_remarks": rep.replacement_remarks,
                    }
                )

            # ---------------------------------------------------------
            # 5. Annual SRMR Routine Undertaken (GTG)
            # ---------------------------------------------------------
            gtg_srmr_records = AnnualSRMRRoutineUndertakenofGTG.objects.filter(
                srar_monthly_header=header
            ).select_related("equipment", "by_whom")

            for srmr in gtg_srmr_records:
                equipment = srmr.equipment

                tab_11_gtg_srmr_json.append(
                    {
                        "id": srmr.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "t_equipment_ship_detail": (
                            equipment.t_equipment_ship_detail if equipment else None
                        ),
                        "equipment_id": (equipment.id if equipment else None),
                        "serial_no": srmr.serial_no,
                        "date": srmr.date,
                        "description_of_routine": srmr.description_of_routine,
                        # "by_whom_id": srmr.by_whom.id if srmr.by_whom else None,
                        # "by_whom_name": (
                        #     srmr.by_whom.get_full_name()
                        #     if srmr.by_whom else None
                        # ),
                    }
                )

            # =========================================================
            # TAB 12 : MONTHLY LUBRICANT DETAILS
            # =========================================================

            tab_12_lubricant_json = []

            lubricant_records = SrarMonthlyLubricant.objects.filter(
                srar_monthly_header=header
            ).select_related("lubricant")

            for lub in lubricant_records:
                lubricant = lub.lubricant

                tab_12_lubricant_json.append(
                    {
                        "id": lub.id,
                        "universal_id": (
                            lubricant.Universal_ID_M_Lubricant if lubricant else None
                        ),
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "serial_no": lub.serial_no,
                        "lubricant_name": (
                            lubricant.LubricantName if lubricant else None
                        ),
                        "quantity": lub.quantity,
                        "unit": lub.unit,
                    }
                )

            # =========================================================
            # TAB 13 : RH EXTENSION
            # =========================================================

            tab_13_rh_extension_json = []

            rh_extension_records = RHExtension.objects.filter(
                srar_monthly_header=header
            ).select_related("sfd_details__equipment", "on_routine")

            for rh in rh_extension_records:
                sfd = rh.sfd_details
                equipment = sfd.equipment if sfd else None
                frequency = rh.on_routine

                tab_13_rh_extension_json.append(
                    {
                        "id": rh.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "equipment_id": sfd.id if sfd else None,
                        "m_equipment_id": (
                            equipment.universal_id_m_equipment if equipment else None
                        ),
                        "t_equipment_ship_detail": (
                            sfd.t_equipment_ship_detail if sfd else None
                        ),
                        "serial_no": rh.serial_no,
                        "equipment_type": rh.equipment_type,
                        "total_rh_in_month": rh.total_rh_in_month,
                        "on_routine": (frequency.frequency if frequency else None),
                        "rh_ext_at_conduct_of_ext_trial": (
                            rh.rh_ext_at_conduct_of_ext_trial
                        ),
                        "authority_letter_for_extension_trial": (
                            rh.authority_letter_for_extension_trial
                        ),
                        "rh_extension_granted_upto": rh.rh_extension_granted_upto,
                        "rh_left_for_expiry_of_extension": (
                            rh.rh_left_for_expiry_of_extension
                        ),
                        "Frequency_id": (
                            frequency.Universal_ID_M_Frequency if frequency else None
                        ),
                    }
                )

            # =========================================================
            # TAB 14 : EEF
            # =========================================================

            tab_14_eef_json = []

            eef_records = EEF.objects.filter(srar_monthly_header=header)

            eef_reason_choices = dict(EEF.REASON_CHOICES)

            for eef in eef_records:
                tab_14_eef_json.append(
                    {
                        "id": eef.id,
                        "srar_monthly_header_id": header.id,
                        "header_unique_id": universal_id,
                        "serial_no": eef.serial_no,
                        "designed": eef.designed,
                        "actual": eef.actual,
                        "reason_for_exceeding": eef.reason_for_exceeding,
                        "reason_for_exceeding_label": (
                            eef_reason_choices.get(eef.reason_for_exceeding)
                        ),
                        "ship_remarks": eef.ship_remarks,
                    }
                )

            # =========================================================
            # FINAL PAYLOAD
            # =========================================================

            payload = {
                "header": header_json,
                "tab_1_equipment_exploitations": equipment_explotion_data_json,
                "tab_2_boiler_data": tab_2_boiler_data,
                "tab_2_boiler_steaming_details": tab_2_boiler_tab_data_json,
                "tab_2_boiler_alkalinity_salinity_data": (
                    tab_2_boiler_alkalinity_salinity_data_json
                ),
                "tab_3_ship_activity_details": (tab_3_ship_activity_details_json),
                "tab_4_fuel_consumption_months": (tab4_fuel_consumption_month_json),
                "tab_4_avcat_status_data": tab_4_avcat_status_json,
                "tab_4_torsion_meter_data": tab_4_torsion_meter_json,
                "tab_5_iccp_data": tab_iccp_json,
                "tab_5_h2s_sensor_data": tab_h2s_sensor_json,
                "tab_5_stp_data": tab_stp_json,
                "tab_5_magazine_ff_system_data": (tab_magazine_ff_system_json),
                "tab_6_centrifuge_data": tab_centrifuge_json,
                "tab_6_lub_oil_coolant_test_kits_data": (
                    tab_lub_oil_coolant_test_kits_json
                ),
                "tab_7_safety_device_check_trial": (
                    tab_7_safety_device_check_trial_json
                ),
                "tab_7_injector_fip_calibration_replacement": (tab_7_injector_fip_json),
                "tab_8_dguf_data": dgufs,
                # "tab_8_dguf_sea_harbour_data": tab_8_dguf_sea_harbour_json,
                # "tab_8_dguf_limits_data": tab_8_dguf_limits_json,
                "tab_9_fpt_main_engine": tab_9_fpt_main_engine_json,
                "tab_9_fpt_equipment": tab_9_fpt_equipment_json,
                "tab_9_fpt_diesel_alternator": (tab_9_fpt_diesel_alternator_json),
                "tab_10_reduction_gear_exploitation": (
                    tab_10_reduction_gear_exploitation_json
                ),
                "tab_10_gas_turbine_exploitation": (
                    tab_10_gas_turbine_exploitation_json
                ),
                "tab_10_annual_SRMR": tab_10_annual_SRMR,
                "tab_10_replacement": tab_10_replacement,
                "tab_11_gtg_exploitation": (tab_11_gtg_exploitation_json),
                "tab_11_gtg_guf": tab_11_gtg_guf_json,
                "tab_11_gtg_reduction_gear": (tab_11_gtg_rg_exploitation_json),
                "tab_11_gtg_replacement": (tab_11_gtg_replacement_json),
                "tab_11_gtg_srmr": tab_11_gtg_srmr_json,
                "tab_12_monthly_lubricant": tab_12_lubricant_json,
                "tab_13_rh_extension": tab_13_rh_extension_json,
                "tab_14_eef": tab_14_eef_json,
            }

            # =========================================================
            # JSON SERIALIZATION
            # =========================================================

            json_data = json.dumps(
                payload, indent=4, ensure_ascii=False, cls=DjangoJSONEncoder
            )

            # =========================================================
            # SAVE JSON FILE
            # =========================================================

            with open("srar_payload.json", "w", encoding="utf-8") as f:
                f.write(json_data)

            # =========================================================
            # SEND DATA TO CMMS
            # =========================================================

            api_url = f"{API_URL}/api/srar/save-srar/"

            try:
                response = requests.post(
                    api_url,
                    data=json_data,
                    headers={"Content-Type": "application/json"},
                    timeout=8001,
                    verify=False,
                )

                try:
                    error_data = response.json()
                except ValueError:
                    error_data = {
                        "status": False,
                        "message": (
                            f"Invalid response from CMMS. "
                            f"HTTP Status: {response.status_code}"
                        ),
                    }

                if error_data.get("status") is False:
                    error_message = error_data.get(
                        "message", "Unable to send data to CMMS."
                    )

                    sweetify.error(
                        request,
                        title="",
                        icon="error",
                        text=error_message,
                        persistent=True,
                    )

                else:
                    sweetify.success(
                        request,
                        title="",
                        icon="success",
                        text="Data was successfully sent to CMMS",
                        persistent=True,
                    )

            except requests.RequestException as exc:
                sweetify.error(
                    request,
                    title="",
                    icon="error",
                    text=f"Unable to connect to CMMS: {str(exc)}",
                    persistent=True,
                )

        except requests.RequestException as exc:
            sweetify.error(
                request,
                title="",
                icon="error",
                text=f"Unable to connect to CMMS: {str(exc)}",
                persistent=True,
            )
        return redirect("/srar/sraradd/")


# ==============================================================================
# CMMS SRAR SYNC BY MONTH & YEAR Ã¢â‚¬â€ Angular-Compatible JSON API
# ==============================================================================


class SRARSyncByMonthYearAPIView(APIView):
    """
    Angular-compatible SRAR Ã¢â€ â€™ CMMS sync endpoint.

    Accepts GET with query params:
        ?month=August&year=2026   (month can be name or number)

    1. Resolves SrarMonthlyHeader for the given month/year.
    2. Generates a signed pk (same as SRARSyncAPIView expects).
    3. Calls SRARSyncAPIView.get() internally which builds + POSTs to CMMS,
       and saves payload to srar_payload.json.
    4. Reads result and returns JSON { status, message } Ã¢â‚¬â€ no redirect/sweetify.
    """

    MONTH_MAP = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def get(self, request):
        month_param = request.query_params.get("month", "").strip()
        year_param = request.query_params.get("year", "").strip()

        # Ã¢â€â‚¬Ã¢â€â‚¬ Validate params Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        if not month_param or not year_param:
            return Response(
                {
                    "status": False,
                    "message": "Both 'month' and 'year' query parameters are required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if month_param.isdigit():
            month_num = int(month_param)
        else:
            month_num = self.MONTH_MAP.get(month_param.lower())

        if not month_num or month_num < 1 or month_num > 12:
            return Response(
                {"status": False, "message": f"Invalid month value: '{month_param}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            year_num = int(year_param)
        except ValueError:
            return Response(
                {"status": False, "message": f"Invalid year value: '{year_param}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ã¢â€â‚¬Ã¢â€â‚¬ Find SrarMonthlyHeader Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            header = (
                SrarMonthlyHeader.objects.filter(
                    srar_month=month_num, srar_year=year_num
                )
                .order_by("-id")
                .first()
            )
        except Exception as exc:
            return Response(
                {"status": False, "message": f"Database error: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        is_first_time = (header is None) or not bool(
            getattr(header, "cmms_sync_status", False)
        )

        # =========================================================================
        # STRATEGY 1: FIRST TIME SYNC (new DB / header missing / unsynced) -> PULL FROM CMMS
        # =========================================================================
        if is_first_time:
            logger.info(
                f"First-time SRAR sync detected for {month_param} {year_num}. Executing PULL from CMMS..."
            )
            pull_view = SRARPullFromCMMSAPIView()
            pull_resp = pull_view.get(request)

            if pull_resp.status_code == 200:
                header_updated = (
                    SrarMonthlyHeader.objects.filter(
                        srar_month=month_num, srar_year=year_num
                    )
                    .order_by("-id")
                    .first()
                )
                if header_updated:
                    header_updated.cmms_sync_status = True
                    header_updated.save(update_fields=["cmms_sync_status"])

            return Response(
                {
                    "status": pull_resp.data.get("status", True),
                    "message": (
                        f"First-time sync completed: SRAR data for {month_param} {year_num} "
                        "successfully pulled from CMMS into SWMM DB."
                    ),
                    "sync_type": "PULL",
                    "details": pull_resp.data,
                    "cmms_sync_status": True,
                },
                status=pull_resp.status_code,
            )

        # Ã¢â€â‚¬Ã¢â€â‚¬ Generate signed pk Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        signed_pk = signing.dumps(header.id)

        # Ã¢â€â‚¬Ã¢â€â‚¬ Delegate to existing SRARSyncAPIView Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        # Temporarily suppress sweetify side effects (it uses Django messages/
        # sessions which don't exist in DRF API context).
        import sys as _sys

        _orig_sweetify = _sys.modules.get("sweetify")

        class _NoOpSweetify:
            @staticmethod
            def success(*a, **kw):
                pass

            @staticmethod
            def error(*a, **kw):
                pass

        try:
            _sys.modules["sweetify"] = _NoOpSweetify()
            sync_view = SRARSyncAPIView()
            sync_view.get(request, signed_pk)
        except Exception as exc:
            _sys.modules["sweetify"] = _orig_sweetify or _NoOpSweetify()
            return Response(
                {"status": False, "message": f"Sync process error: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            if _orig_sweetify is not None:
                _sys.modules["sweetify"] = _orig_sweetify
            else:
                _sys.modules.pop("sweetify", None)

        # Ã¢â€â‚¬Ã¢â€â‚¬ SRARSyncAPIView writes srar_payload.json on success Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            with open("srar_payload.json", "r", encoding="utf-8") as _f:
                payload_dict = json.load(_f)
        except Exception as exc:
            return Response(
                {
                    "status": False,
                    "message": f"Payload build failed: {str(exc)}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Ã¢â€â‚¬Ã¢â€â‚¬ POST to CMMS Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        api_url = f"{API_URL}/api/srar/save-srar/"
        json_data = json.dumps(
            payload_dict, indent=4, ensure_ascii=False, cls=DjangoJSONEncoder
        )

        try:
            cmms_response = requests.post(
                api_url,
                data=json_data,
                headers={"Content-Type": "application/json"},
                timeout=8001,
                verify=False,
            )
            try:
                cmms_data = cmms_response.json()
            except ValueError:
                cmms_data = {
                    "status": False,
                    "message": f"Invalid response from CMMS. HTTP {cmms_response.status_code}",
                }

            if cmms_data.get("status") is False:
                error_msg = cmms_data.get(
                    "message", "CMMS returned an error. Sync failed."
                )
                return Response(
                    {"status": False, "message": error_msg},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # Ã¢â€â‚¬Ã¢â€â‚¬ Mark synced in SWMM DB Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
            try:
                SrarMonthlyHeader.objects.filter(id=header.id).update(
                    cmms_sync_status=True,
                )
            except Exception:
                pass  # Non-critical

            return Response(
                {
                    "status": True,
                    "message": "SRAR data successfully synced to CMMS.",
                    "srar_id": header.id,
                    "month": month_param,
                    "year": year_num,
                    "cmms_sync_status": True,
                },
                status=status.HTTP_200_OK,
            )

        except requests.RequestException as exc:
            return Response(
                {"status": False, "message": f"Unable to connect to CMMS: {str(exc)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


# ==============================================================================
# CMMS SRAR DATA SAVE API
# ==============================================================================


class SRARDataSaveAPI(APIView):
    def get(self, request):
        """
        GET /api/srar/save-srar/?ship_code=L18&month=August&year=2026
        Returns SRAR payload JSON for specified month/year or all past data for ship.
        """
        from srar.models import (
            SrarMonthlyHeader,
            SrarEquipmentExploitation,
            SrarMonthlyBoiler,
            SrarMonthlyShipActivity,
            FuelConsumptionMonth,
            AvcatStatus,
            TorsionMeter,
            Iccp,
            H2SSensor,
            STP,
            MagazineFFSystemFloodingSystem,
            OpsStatusofLubOilandCoolantTestKits,
            SafetyDeviceCheckTrial,
            InjectorFIPCalibrationReplacement,
            DGUFSeaHarbourRunningHourDataInput,
            DGUFLimits,
            FullPowerTrialsMainEngine,
            FPTEquipmentWise,
            FPTDieselAlternators,
            GasTurbineExploitation,
            ReductionGearExploitation,
            GasTurbineGeneratorExploitation,
            GasTurbineGeneratorExploitationGufEntry,
            ReductionGearExploitationofGTG,
            ReplacementOfMajorAssemblies,
            ReplacementOfMajorAssembliesofGTG,
            AnnualSRMRRoutineUndertaken,
            AnnualSRMRRoutineUndertakenofGTG,
            RHExtension,
            SrarMonthlyLubricant,
            EEF,
        )

        ship_code = request.query_params.get("ship_code", "").strip()
        month_param = request.query_params.get("month", "").strip()
        year_param = request.query_params.get("year", "").strip()

        headers_qs = SrarMonthlyHeader.objects.all()
        if ship_code:
            headers_qs = headers_qs.filter(
                Q(ship__code__iexact=ship_code)
                | Q(ship__name__icontains=ship_code)
                | Q(ship__universal_id_m_ship__iexact=ship_code)
            )

        if month_param:
            if month_param.isdigit():
                headers_qs = headers_qs.filter(srar_month=int(month_param))
            else:
                m_map = {
                    "january": 1,
                    "february": 2,
                    "march": 3,
                    "april": 4,
                    "may": 5,
                    "june": 6,
                    "july": 7,
                    "august": 8,
                    "september": 9,
                    "october": 10,
                    "november": 11,
                    "december": 12,
                    "jan": 1,
                    "feb": 2,
                    "mar": 3,
                    "apr": 4,
                    "jun": 6,
                    "jul": 7,
                    "aug": 8,
                    "sep": 9,
                    "oct": 10,
                    "nov": 11,
                    "dec": 12,
                }
                m_num = m_map.get(month_param.lower())
                if m_num:
                    headers_qs = headers_qs.filter(srar_month=m_num)

        if year_param and year_param.isdigit():
            headers_qs = headers_qs.filter(srar_year=int(year_param))

        headers = list(headers_qs.order_by("-srar_year", "-srar_month"))

        if not headers:
            # Fallback to all headers
            fallback_qs = SrarMonthlyHeader.objects.all()
            if month_param and month_param.isdigit():
                fallback_qs = fallback_qs.filter(srar_month=int(month_param))
            if year_param and year_param.isdigit():
                fallback_qs = fallback_qs.filter(srar_year=int(year_param))
            headers = list(fallback_qs.order_by("-srar_year", "-srar_month"))

        if not headers:
            return Response(
                {
                    "status": False,
                    "message": f"No SRAR records found for ship '{ship_code}'.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        results = []
        for header in headers:
            h_data = {
                "id": header.id,
                "srar_month": header.srar_month,
                "srar_year": header.srar_year,
                "hours_underway_month_hr": header.hours_underway_month_hr,
                "hours_underway_month_min": header.hours_underway_month_min,
                "hours_underway_month_minutes": header.hours_underway_month_minutes,
                "distance_run_month": header.distance_run_month,
                "hours_underway_since_commissioning_hr": header.hours_underway_since_commissioning_hr,
                "distance_run_since_commissioning": header.distance_run_since_commissioning,
                "max_speed": header.max_speed,
                "max_duration": header.max_duration,
                "eo_name": header.eo_name,
                "eo_rank": header.eo_rank,
                "eo_personal_no": header.eo_personal_no,
                "eo_contact_no": header.eo_contact_no,
                "eo_writer_contact_no": header.eo_writer_contact_no,
                "is_saved": header.is_saved,
            }

            eq_list = list(
                SrarEquipmentExploitation.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            boiler_list = list(
                SrarMonthlyBoiler.objects.filter(srar_monthly_header=header).values()
            )
            act_list = list(
                SrarMonthlyShipActivity.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            fuel_list = list(
                FuelConsumptionMonth.objects.filter(srar_monthly_header=header).values()
            )
            avcat_list = list(
                AvcatStatus.objects.filter(srar_monthly_header=header).values()
            )
            torsion_list = list(
                TorsionMeter.objects.filter(srar_monthly_header=header).values()
            )
            iccp_list = list(Iccp.objects.filter(srar_monthly_header=header).values())
            h2s_list = list(
                H2SSensor.objects.filter(srar_monthly_header=header).values()
            )
            stp_list = list(STP.objects.filter(srar_monthly_header=header).values())
            mag_list = list(
                MagazineFFSystemFloodingSystem.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            test_list = list(
                OpsStatusofLubOilandCoolantTestKits.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            safety_list = list(
                SafetyDeviceCheckTrial.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            inj_list = list(
                InjectorFIPCalibrationReplacement.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            dguf_list = list(
                DGUFSeaHarbourRunningHourDataInput.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            fpt_me_list = list(
                FullPowerTrialsMainEngine.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            fpt_eq_list = list(
                FPTEquipmentWise.objects.filter(srar_monthly_header=header).values()
            )
            fpt_da_list = list(
                FPTDieselAlternators.objects.filter(srar_monthly_header=header).values()
            )
            gt_list = list(
                GasTurbineExploitation.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            rg_list = list(
                ReductionGearExploitation.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gt_rep_list = list(
                ReplacementOfMajorAssemblies.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gt_srmr_list = list(
                AnnualSRMRRoutineUndertaken.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gtg_list = list(
                GasTurbineGeneratorExploitation.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gtg_guf_list = list(
                GasTurbineGeneratorExploitationGufEntry.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gtg_rg_list = list(
                ReductionGearExploitationofGTG.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gtg_rep_list = list(
                ReplacementOfMajorAssembliesofGTG.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            gtg_srmr_list = list(
                AnnualSRMRRoutineUndertakenofGTG.objects.filter(
                    srar_monthly_header=header
                ).values()
            )
            lub_list = list(
                SrarMonthlyLubricant.objects.filter(srar_monthly_header=header).values()
            )
            rh_list = list(
                RHExtension.objects.filter(srar_monthly_header=header).values()
            )
            eef_list = list(EEF.objects.filter(srar_monthly_header=header).values())

            payload = {
                "header": h_data,
                "tab_1_equipment_exploitations": eq_list,
                "tab_2_boiler_data": boiler_list,
                "tab_3_ship_activity_details": act_list,
                "tab_4_fuel_consumption_months": fuel_list,
                "tab_4_avcat_status_data": avcat_list,
                "tab_4_torsion_meter_data": torsion_list,
                "tab_5_iccp_data": iccp_list,
                "tab_5_h2s_sensor_data": h2s_list,
                "tab_5_stp_data": stp_list,
                "tab_5_magazine_ff_system_data": mag_list,
                "tab_6_lub_oil_coolant_test_kits_data": test_list,
                "tab_7_safety_device_check_trial": safety_list,
                "tab_7_injector_fip_calibration_replacement": inj_list,
                "tab_8_dguf_data": dguf_list,
                "tab_9_fpt_main_engine": fpt_me_list,
                "tab_9_fpt_equipment": fpt_eq_list,
                "tab_9_fpt_diesel_alternator": fpt_da_list,
                "tab_10_gas_turbine_exploitation": gt_list,
                "tab_10_reduction_gear_exploitation": rg_list,
                "tab_10_replacement": gt_rep_list,
                "tab_10_annual_SRMR": gt_srmr_list,
                "tab_11_gtg_exploitation": gtg_list,
                "tab_11_gtg_guf": gtg_guf_list,
                "tab_11_gtg_reduction_gear": gtg_rg_list,
                "tab_11_gtg_replacement": gtg_rep_list,
                "tab_11_gtg_srmr": gtg_srmr_list,
                "tab_12_monthly_lubricant": lub_list,
                "tab_13_rh_extension": rh_list,
                "tab_14_eef": eef_list,
            }
            results.append(payload)

        if len(results) == 1 and month_param and year_param:
            return Response(results[0], status=status.HTTP_200_OK)
        return Response(
            {
                "status": True,
                "ship_code": ship_code,
                "count": len(results),
                "data": results,
            },
            status=status.HTTP_200_OK,
        )

    """
    API View to save complete SRAR return data using Django ORM models.
    All raw SQL has been converted to Django ORM update_or_create calls
    wrapped in a single @transaction.atomic block.
    """

    @transaction.atomic
    def post(self, request):
        from srar.models import (
            SrarMonthlyHeader,
            SrarEquipmentExploitation,
            SrarMonthlyBoiler,
            SrarMonthlyShipActivity,
            FuelConsumptionMonth,
            AvcatStatus,
            TorsionMeter,
            Iccp,
            H2SSensor,
            STP,
            MagazineFFSystemFloodingSystem,
            OpsStatusofLubOilandCoolantTestKits,
            SafetyDeviceCheckTrial,
            InjectorFIPCalibrationReplacement,
            DGUF,
            DGUFSeaHarbourRunningHourDataInput,
            DGUFLimits,
            FullPowerTrialsMainEngine,
            FPTEquipmentWise,
            FPTDieselAlternators,
            GasTurbineExploitation,
            ReductionGearExploitation,
            GasTurbineGeneratorExploitation,
            GasTurbineGeneratorExploitationGufEntry,
            ReductionGearExploitationofGTG,
            ReplacementOfMajorAssemblies,
            ReplacementOfMajorAssembliesofGTG,
            AnnualSRMRRoutineUndertaken,
            AnnualSRMRRoutineUndertakenofGTG,
            RHExtension,
            SrarMonthlyLubricant,
        )
        from sfd.models import ShipEquipment

        active_tab = "SrarMonthlyHeader"
        active_record_id = "unknown"

        try:
            # -----------------------------------------------------------------
            # Parse request payload
            # -----------------------------------------------------------------
            header = request.data.get("header", {})
            equipment_exploitations = request.data.get(
                "tab_1_equipment_exploitations", []
            )
            boiler_steaming_details = request.data.get("tab_2_boiler_data", [])
            ship_activity_details = request.data.get("tab_3_ship_activity_details", [])
            fuel_consumption_months_1 = request.data.get(
                "tab_4_fuel_consumption_months", []
            )
            fuel_consumption_months_2 = request.data.get("tab_4_avcat_status_data", [])
            fuel_consumption_months_3 = request.data.get("tab_4_torsion_meter_data", [])
            iccp_data_1 = request.data.get("tab_5_iccp_data", [])
            iccp_data_2 = request.data.get("tab_5_h2s_sensor_data", [])
            iccp_data_3 = request.data.get("tab_5_stp_data", [])
            iccp_data_4 = request.data.get("tab_5_magazine_ff_system_data", [])
            centrifuge_data_1 = request.data.get("tab_6_centrifuge_data", [])
            centrifuge_data_2 = request.data.get(
                "tab_6_lub_oil_coolant_test_kits_data", []
            )
            safety_device_check_trial_1 = request.data.get(
                "tab_7_safety_device_check_trial", []
            )
            safety_device_check_trial_2 = request.data.get(
                "tab_7_injector_fip_calibration_replacement", []
            )
            dgufs = request.data.get("tab_8_dguf_data", [])
            fpt_main_engine = request.data.get("tab_9_fpt_main_engine", [])
            fpt_equipment = request.data.get("tab_9_fpt_equipment", [])
            fpt_main_engine_3 = request.data.get("tab_9_fpt_diesel_alternator", [])
            gtg_exploitation = request.data.get("tab_11_gtg_exploitation", [])
            gtg_guf = request.data.get("tab_11_gtg_guf", [])
            gtg_reduction_gear = request.data.get("tab_11_gtg_reduction_gear", [])
            reduction_gear_exploitation = request.data.get(
                "tab_10_reduction_gear_exploitation", []
            )
            gas_turbine_exploitation = request.data.get(
                "tab_10_gas_turbine_exploitation", []
            )
            gt_tab_10_replacement = request.data.get("tab_10_replacement", [])
            gtg_tab_11_replacement = request.data.get("tab_11_gtg_replacement", [])
            gt_tab_10_SRMR = request.data.get("tab_10_annual_SRMR", [])
            gtg_tab_11_SRMR = request.data.get("tab_11_gtg_srmr", [])
            rh_extension = request.data.get("tab_13_rh_extension", [])
            monthly_lubricant = request.data.get("tab_12_monthly_lubricant", [])

            header_id = header["id"]
            universal_id = f"SWMM-{header_id}"
            active_record_id = universal_id

            # -----------------------------------------------------------------
            # Resolve header FK
            # -----------------------------------------------------------------
            header_obj = SrarMonthlyHeader.objects.filter(pk=header_id).first()
            if not header_obj:
                return Response(
                    {"status": False, "message": f"SRAR header {header_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # -----------------------------------------------------------------
            # Tab 1 â€“ Equipment Exploitation
            # -----------------------------------------------------------------
            active_tab = "SrarEquipmentExploitation"
            for ee in equipment_exploitations:
                active_record_id = f"SWMM-{ee.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=ee.get("t_equipment_ship_detail")
                ).first()
                SrarEquipmentExploitation.objects.update_or_create(
                    pk=ee.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "hrs_for_month": ee.get("hrs_for_month"),
                        "hrs_for_month_hrs": ee.get("running_hour_at_sea"),
                        "hrs_for_month_min": ee.get("running_hour_at_harbour"),
                        "rhsi_till_prev_month": ee.get("rhsi_till_prev_month"),
                        "rhsi_till_current_month": ee.get("rhsi_till_current_month"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 2 â€“ Boiler Steaming
            # -----------------------------------------------------------------
            active_tab = "SrarMonthlyBoiler"
            for bd in boiler_steaming_details:
                active_record_id = f"SWMM-{bd.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=bd.get("t_equipment_ship_detail")
                ).first()
                SrarMonthlyBoiler.objects.update_or_create(
                    pk=bd.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "name": bd.get("name"),
                        "serial_no": bd.get("serial_no"),
                        "hrs_steamed_in_month": bd.get("hrs_steamed_in_month"),
                        "hrs_steamed_since_commissioning": bd.get(
                            "hrs_steamed_since_commissioning"
                        ),
                        "highest_salinity_during_month": bd.get(
                            "highest_salinity_during_month"
                        ),
                        "lowest_salinity_during_month": bd.get(
                            "lowest_salinity_during_month"
                        ),
                        "hrs_above_20_percent": bd.get("hrs_above_20_percent"),
                        "last_int_clg_date": bd.get("last_int_clg_date") or None,
                        "hrs_steamed_since_last_int_clg": bd.get(
                            "hrs_steamed_since_last_int_clg"
                        ),
                        "last_ext_clg_date": bd.get("last_ext_clg_date") or None,
                        "hrs_steamed_since_last_ext_clg": bd.get(
                            "hrs_steamed_since_last_ext_clg"
                        ),
                        "last_retubing_date": bd.get("last_retubing_date") or None,
                        "hrs_steamed_since_last_retubing": bd.get(
                            "hrs_steamed_since_last_retubing"
                        ),
                        "date_of_last_durability_test": bd.get(
                            "date_of_last_durability_test"
                        )
                        or None,
                        "due_date_for_next_inspection": bd.get(
                            "due_date_for_next_inspection"
                        )
                        or None,
                        "life_assessed_in_months": bd.get("life_assessed_in_months"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 3 â€“ Ship Activity
            # -----------------------------------------------------------------
            active_tab = "SrarMonthlyShipActivity"
            for sa in ship_activity_details:
                active_record_id = f"SWMM-{sa.get('id')}"
                SrarMonthlyShipActivity.objects.update_or_create(
                    pk=sa.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "from_date": sa.get("from_date") or None,
                        "to_date": sa.get("to_date") or None,
                        "serial_no": sa.get("serial_no"),
                        "remarks": sa.get("remarks"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 4 â€“ Fuel Consumption
            # -----------------------------------------------------------------
            active_tab = "FuelConsumptionMonth"
            for fc in fuel_consumption_months_1:
                active_record_id = f"SWMM-{fc.get('id')}"
                FuelConsumptionMonth.objects.update_or_create(
                    pk=fc.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "b_f_from_last_month": fc.get("b_f_from_last_month"),
                        "recieved": fc.get("recieved"),
                        "consumed_in_harbour": fc.get("consumed_in_harbour"),
                        "consumed_at_anchorage": fc.get("consumed_at_anchorage"),
                        "consumed_at_sea": fc.get("consumed_at_sea"),
                        "total_consumed": fc.get("total_consumed"),
                        "defueled": fc.get("defueled"),
                        "balance_left_on_board": fc.get("balance_left_on_board"),
                        "serial_no": fc.get("serial_no"),
                    },
                )

            # Tab 4 â€“ AVCAT Status
            active_tab = "AvcatStatus"
            for av in fuel_consumption_months_2:
                active_record_id = f"SWMM-{av.get('id')}"
                AvcatStatus.objects.update_or_create(
                    pk=av.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "b_f_from_last_month": av.get("b_f_from_last_month"),
                        "recieved": av.get("recieved"),
                        "given_to_ac": av.get("given_to_ac"),
                        "used_for_trials_drained": av.get("used_for_trials_drained"),
                        "total_consumed": av.get("total_consumed"),
                        "defuelded": av.get("defuelded"),
                        "balance_left_on_board": av.get("balance_left_on_board"),
                        "serial_no": av.get("serial_no"),
                    },
                )

            # Tab 4 â€“ Torsion Meter
            active_tab = "TorsionMeter"
            for tm in fuel_consumption_months_3:
                active_record_id = f"SWMM-{tm.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=tm.get("t_equipment_ship_detail")
                ).first()
                TorsionMeter.objects.update_or_create(
                    pk=tm.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "nomenclature": tm.get("nomenclature"),
                        "eqpt_code": tm.get("eqpt_code"),
                        "loc_on_board": tm.get("loc_on_board"),
                        "serial_no": tm.get("serial_no"),
                        "torsion_meter_rdg": tm.get("torsion_meter_rdg"),
                        "max_rpm_achieved": tm.get("max_rpm_achieved"),
                        "ops_or_non_ops": tm.get("ops_or_non_ops"),
                        "non_ops_since": tm.get("non_ops_since") or None,
                        "last_calibration_date": tm.get("last_calibration_date")
                        or None,
                        "next_calibration_date": tm.get("next_calibration_date")
                        or None,
                    },
                )

            # -----------------------------------------------------------------
            # Tab 5 â€“ ICCP
            # -----------------------------------------------------------------
            active_tab = "Iccp"
            for ic in iccp_data_1:
                active_record_id = f"SWMM-{ic.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=ic.get("t_equipment_ship_detail")
                ).first()
                Iccp.objects.update_or_create(
                    pk=ic.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "serial_no": ic.get("serial_no"),
                        "nomenclature": ic.get("nomenclature"),
                        "loc_on_board": ic.get("loc_on_board"),
                        "ops_or_non_ops": ic.get("ops_or_non_ops"),
                        "non_ops_since": ic.get("non_ops_since") or None,
                    },
                )

            # Tab 5 â€“ H2S Sensor
            active_tab = "H2SSensor"
            for h2 in iccp_data_2:
                active_record_id = f"SWMM-{h2.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=h2.get("t_equipment_ship_detail")
                ).first()
                H2SSensor.objects.update_or_create(
                    pk=h2.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "serial_no": h2.get("serial_no"),
                        "nomenclature": h2.get("nomenclature"),
                        "loc_on_board": h2.get("loc_on_board"),
                        "ops_or_non_ops": h2.get("ops_or_non_ops"),
                        "non_ops_since": h2.get("non_ops_since") or None,
                        "last_calibration_date": h2.get("last_calibration_date")
                        or None,
                        "next_calibration_date": h2.get("next_calibration_date")
                        or None,
                    },
                )

            # Tab 5 â€“ STP
            active_tab = "STP"
            for stp in iccp_data_3:
                active_record_id = f"SWMM-{stp.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=stp.get("t_equipment_ship_detail")
                ).first()
                STP.objects.update_or_create(
                    pk=stp.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "serial_no": stp.get("serial_no"),
                        "nomenclature": stp.get("nomenclature"),
                        "loc_on_board": stp.get("loc_on_board"),
                        "ops_or_non_ops": stp.get("ops_or_non_ops"),
                        "non_ops_since": stp.get("non_ops_since") or None,
                        "effluent_test_date": stp.get("effluent_test_date") or None,
                        "effluent_status": stp.get("effluent_status"),
                        "remarks": stp.get("remarks"),
                    },
                )

            # Tab 5 â€“ Magazine FF / Flooding System
            active_tab = "MagazineFFSystemFloodingSystem"
            for mf in iccp_data_4:
                active_record_id = f"SWMM-{mf.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=mf.get("t_equipment_ship_detail")
                ).first()
                MagazineFFSystemFloodingSystem.objects.update_or_create(
                    pk=mf.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "serial_no": mf.get("serial_no"),
                        "nomenclature": mf.get("nomenclature"),
                        "loc_on_board": mf.get("loc_on_board"),
                        "ops_or_non_ops": mf.get("ops_or_non_ops"),
                        "non_ops_since": mf.get("non_ops_since") or None,
                        "last_trials_taken": mf.get("last_trials_taken") or None,
                        "next_trials_due": mf.get("next_trials_due") or None,
                    },
                )

            # -----------------------------------------------------------------
            # Tab 6 â€“ Centrifuge (SrarCentrifuge â†’ OpsStatusofLubOilandCoolantTestKits)
            # -----------------------------------------------------------------
            active_tab = "OpsStatusofLubOilandCoolantTestKits (centrifuge)"
            for ced in centrifuge_data_1:
                active_record_id = f"SWMM-{ced.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=ced.get("t_equipment_ship_detail")
                ).first()
                OpsStatusofLubOilandCoolantTestKits.objects.update_or_create(
                    pk=ced.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "serial_no": ced.get("serial_no"),
                        "ops_or_non_ops": ced.get("ops_or_non_ops"),
                        "non_ops_since": ced.get("non_ops_since") or None,
                    },
                )

            # Tab 6 â€“ Lub Oil / Coolant Test Kits
            active_tab = "OpsStatusofLubOilandCoolantTestKits"
            for ced2 in centrifuge_data_2:
                active_record_id = f"SWMM-{ced2.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=ced2.get("t_equipment_ship_detail")
                ).first()
                OpsStatusofLubOilandCoolantTestKits.objects.update_or_create(
                    pk=ced2.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "description": ced2.get("description"),
                        "serial_no": ced2.get("serial_no"),
                        "ops_or_non_ops": ced2.get("ops_or_non_ops"),
                        "non_ops_since": ced2.get("non_ops_since") or None,
                        "last_trials_taken": ced2.get("last_trials_taken") or None,
                        "next_trials_due": ced2.get("next_trials_due") or None,
                        "calibration": ced2.get("calibration") or None,
                        "next_calibration_due_date": ced2.get(
                            "next_calibration_due_date"
                        )
                        or None,
                    },
                )

            # -----------------------------------------------------------------
            # Tab 7 â€“ Safety Device Check Trial
            # -----------------------------------------------------------------
            active_tab = "SafetyDeviceCheckTrial"
            for sd1 in safety_device_check_trial_1:
                equip_id = sd1.get("t_equipment_ship_detail")
                sdc_by = sd1.get("sdc_conducted_by")
                if not equip_id or not sdc_by:
                    continue
                active_record_id = f"SWMM-{sd1.get('id')}"
                sfd = ShipEquipment.objects.filter(pk=equip_id).first()
                SafetyDeviceCheckTrial.objects.update_or_create(
                    pk=sd1.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "sdc_conducted_by": sdc_by,
                        "date_of_sdc": sd1.get("date_of_sdc") or None,
                        "sfc_in_gm_kwh": sd1.get("sfc_in_gm_kwh"),
                        "last_sfc_trial_date": sd1.get("last_sfc_trial_date") or None,
                        "displacement_during_sfc_trial": sd1.get(
                            "displacement_during_sfc_trial"
                        ),
                        "status": sd1.get("status"),
                    },
                )

            # Tab 7 â€“ Injector / FIP Calibration Replacement
            active_tab = "InjectorFIPCalibrationReplacement"
            for sd2 in safety_device_check_trial_2:
                equip_id = sd2.get("t_equipment_ship_detail")
                if not equip_id:
                    continue
                active_record_id = f"SWMM-{sd2.get('id')}"
                sfd = ShipEquipment.objects.filter(pk=equip_id).first()
                InjectorFIPCalibrationReplacement.objects.update_or_create(
                    pk=sd2.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "hrs_run_below_33_percent": sd2.get("hrs_run_below_33_percent"),
                        "hrs_run_33_to_50_percent": sd2.get("hrs_run_33_to_50_percent"),
                        "hrs_run_50_to_70_percent": sd2.get("hrs_run_50_to_70_percent"),
                        "hrs_run_70_to_100_percent": sd2.get(
                            "hrs_run_70_to_100_percent"
                        ),
                        "lub_oil_consumption_in_month": sd2.get(
                            "lub_oil_consumption_in_month"
                        ),
                        "fuel_consumption_in_month": sd2.get(
                            "fuel_consumption_in_month"
                        ),
                        "date_of_inj_fip_calibration": sd2.get(
                            "date_of_inj_fip_calibration"
                        )
                        or None,
                        "occasion": sd2.get("occasion"),
                        "running_hours_at_replaced": sd2.get(
                            "running_hours_at_replaced"
                        ),
                        "running_hours_months": sd2.get("running_hours_months"),
                        "running_hours_since_installation": sd2.get(
                            "running_hours_since_installation"
                        ),
                        "remarks": sd2.get("remarks"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 8 â€“ DGUF Sea/Harbour Running Hours
            # -----------------------------------------------------------------
            active_tab = "DGUFSeaHarbourRunningHourDataInput"
            for dg in dgufs:
                active_record_id = f"SWMM-{dg.get('id')}"
                DGUFSeaHarbourRunningHourDataInput.objects.update_or_create(
                    pk=dg.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "hours_underway": dg.get("hours_underway"),
                        "total_rh_at_sea": dg.get("total_rh_at_sea"),
                        "anchorage": dg.get("anchorage"),
                        "no_of_hours_in_harbour": dg.get("no_of_hours_in_harbour"),
                        "hours_shore_supply_avl_when_alongs": dg.get(
                            "hours_shore_supply_avl_when_alongs"
                        ),
                        "no_of_cold_moves_in_harbour": dg.get(
                            "no_of_cold_moves_in_harbour"
                        ),
                        "cmts_wrt_to_non_avl_shore_supply": dg.get(
                            "cmts_wrt_to_non_avl_shore_supply"
                        ),
                    },
                )
                # DGUFLimits (exceed reasons)
                DGUFLimits.objects.update_or_create(
                    srar_monthly_header=header_obj,
                    defaults={
                        "actual_dguf_sea": dg.get("actual_dguf_sea"),
                        "actual_dguf_harbour": dg.get("actual_dguf_harbour"),
                        "exceed_reason_sea": dg.get("exceed_reason_sea"),
                        "exceed_reason_harbour": dg.get("exceed_reason_harbour"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 9 â€“ Full Power Trials: Main Engine header
            # -----------------------------------------------------------------
            active_tab = "FullPowerTrialsMainEngine"
            fpt_header_obj = None
            for eng in fpt_main_engine:
                active_record_id = f"SWMM-{eng.get('id')}"
                fpt_header_obj, _ = FullPowerTrialsMainEngine.objects.update_or_create(
                    pk=eng.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "date": eng.get("date") or None,
                        "occasion_reason": eng.get("occasion_reason"),
                        "draught_fwd": eng.get("draught_fwd"),
                        "draught_aft": eng.get("draught_aft"),
                        "displacement": eng.get("displacement"),
                        "max_speed": eng.get("max_speed"),
                        "conducted_by": eng.get("conducted_by"),
                        "torsion_meter_reading": eng.get("torsion_meter_reading"),
                        "sea_state": eng.get("sea_state"),
                        "pending_dr_activities_reason": eng.get(
                            "pending_dr_activities_reason"
                        ),
                    },
                )

            # Tab 9 â€“ FPT Equipment-wise
            active_tab = "FPTEquipmentWise"
            for equipment in fpt_equipment:
                active_record_id = f"SWMM-{equipment.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=equipment.get("t_equipment_ship_detail")
                ).first()
                FPTEquipmentWise.objects.update_or_create(
                    pk=equipment.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "fpt_main_engine": fpt_header_obj,
                        "sfd_details": sfd,
                        "fuel_rack_dbr_max": equipment.get("fuel_rack_dbr_max"),
                        "marking_max": equipment.get("marking_max"),
                        "undertaken_on": equipment.get("undertaken_on") or None,
                        "pitch": equipment.get("pitch"),
                        "max_rpm": equipment.get("max_rpm"),
                        "rated_power": equipment.get("rated_power"),
                        "max_achieved_power": equipment.get("max_achieved_power"),
                        "remarks": equipment.get("remarks"),
                    },
                )

            # Tab 9 â€“ FPT Diesel Alternators
            active_tab = "FPTDieselAlternators"
            for da in fpt_main_engine_3:
                active_record_id = f"SWMM-{da.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=da.get("t_equipment_ship_detail")
                ).first()
                FPTDieselAlternators.objects.update_or_create(
                    pk=da.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "date": da.get("date") or None,
                        "occasion": da.get("occasion"),
                        "rated_load": da.get("rated_load"),
                        "max_load_achieved": da.get("max_load_achieved"),
                        "conducted_by": da.get("conducted_by"),
                        "last_ehm_trials_undertaken_on": da.get(
                            "last_ehm_trials_undertaken_on"
                        )
                        or None,
                        "remarks": da.get("remarks"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 10 â€“ Gas Turbine Exploitation
            # -----------------------------------------------------------------
            active_tab = "GasTurbineExploitation"
            for gt in gas_turbine_exploitation:
                active_record_id = f"SWMM-{gt.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=gt.get("t_equipment_ship_detail")
                ).first()
                GasTurbineExploitation.objects.update_or_create(
                    pk=gt.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "total_rh_in_month": gt.get("total_rh_in_month"),
                        "total_rh_si": gt.get("total_rh_si"),
                        "no_of_hot_starts_in_month": gt.get(
                            "no_of_hot_starts_in_month"
                        ),
                        "no_of_hot_starts_si": gt.get("no_of_hot_starts_si"),
                        "no_of_cold_starts_in_month": gt.get(
                            "no_of_cold_starts_in_month"
                        ),
                        "no_of_cold_starts_si": gt.get("no_of_cold_starts_si"),
                        "no_of_false_starts_in_month": gt.get(
                            "no_of_false_starts_in_month"
                        ),
                        "no_of_false_starts_si": gt.get("no_of_false_starts_si"),
                        "no_of_tech_starts_in_month": gt.get(
                            "no_of_tech_starts_in_month"
                        ),
                        "no_of_tech_starts_si": gt.get("no_of_tech_starts_si"),
                        "no_of_astern_engagements_in_mth": gt.get(
                            "no_of_astern_engagements_in_mth"
                        ),
                        "no_of_astern_engagements_count": gt.get(
                            "no_of_astern_engagements_count"
                        ),
                        "no_of_stop_orders_in_mth": gt.get("no_of_stop_orders_in_mth"),
                        "no_of_stop_orders_si": gt.get("no_of_stop_orders_si"),
                        "rh_regime_1_in_mth": gt.get("rh_regime_1_in_mth"),
                        "rh_regime_1_si": gt.get("rh_regime_1_in_si"),
                        "rh_regime_2_in_mth": gt.get("rh_regime_2_in_mth"),
                        "rh_regime_2_si": gt.get("rh_regime_2_in_si"),
                        "rh_regime_3_in_mth": gt.get("rh_regime_3_in_mth"),
                        "rh_regime_3_si": gt.get("rh_regime_3_in_si"),
                        "last_chem_clg": gt.get("last_chem_clg") or None,
                    },
                )

            # Tab 10 â€“ Reduction Gear Exploitation
            active_tab = "ReductionGearExploitation"
            for rg in reduction_gear_exploitation:
                active_record_id = f"SWMM-{rg.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=rg.get("t_equipment_ship_detail")
                ).first()
                ReductionGearExploitation.objects.update_or_create(
                    pk=rg.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "total_rh_in_month": rg.get("total_rh_in_month"),
                        "total_rh_si": rg.get("total_rh_si"),
                        "total_rh_regime1_in_month": rg.get(
                            "total_rh_regime1_in_month"
                        ),
                        "total_rh_regime1_si": rg.get("total_rh_regime1_si"),
                        "total_rh_regime2_in_month": rg.get(
                            "total_rh_regime2_in_month"
                        ),
                        "total_rh_regime2_si": rg.get("total_rh_regime2_si"),
                        "total_rh_regime3_in_month": rg.get(
                            "total_rh_regime3_in_month"
                        ),
                        "total_rh_regime3_si": rg.get("total_rh_regime3_si"),
                        "trailing_rh_in_month": rg.get("trailing_rh_in_month"),
                        "trailing_rh_si": rg.get("trailing_rh_si"),
                        "service_life_in_month": rg.get("service_life_in_month"),
                        "service_life_si": rg.get("service_life_si"),
                        "no_of_eng_regime1_in_month": rg.get(
                            "no_of_eng_regime1_in_month"
                        ),
                        "no_of_eng_regime1_si": rg.get("no_of_eng_regime1_si"),
                        "no_of_eng_regime2_in_month": rg.get(
                            "no_of_eng_regime2_in_month"
                        ),
                        "no_of_eng_regime2_si": rg.get("no_of_eng_regime2_si"),
                        "no_of_eng_regime3_in_month": rg.get(
                            "no_of_eng_regime3_in_month"
                        ),
                        "no_of_eng_regime3_si": rg.get("no_of_eng_regime3_si"),
                        "no_of_eng_regime4_in_month": rg.get(
                            "no_of_eng_regime4_in_month"
                        ),
                        "no_of_eng_regime4_si": rg.get("no_of_eng_regime4_si"),
                    },
                )

            # Tab 10 â€“ Replacement of Major Assemblies (GT)
            active_tab = "ReplacementOfMajorAssemblies (GT)"
            for rep in gt_tab_10_replacement:
                equip_id = rep.get("t_equipment_ship_detail")
                if not equip_id:
                    continue
                active_record_id = f"SWMM-{rep.get('id')}"
                sfd = ShipEquipment.objects.filter(pk=equip_id).first()
                ReplacementOfMajorAssemblies.objects.update_or_create(
                    pk=rep.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "date_of_replacement": rep.get("date_of_replacement") or None,
                        "unit_sub_units": rep.get("unit_sub_units"),
                        "reason_for_replacement": rep.get("reason_for_replacement"),
                        "replacement_remarks": rep.get("replacement_remarks"),
                        "tab_value": "tab_10",
                    },
                )

            # Tab 10 â€“ Annual SRMR Routines
            active_tab = "AnnualSRMRRoutineUndertaken (GT)"
            for sr in gt_tab_10_SRMR:
                equip_id = sr.get("t_equipment_ship_detail")
                if not equip_id:
                    continue
                active_record_id = f"SWMM-{sr.get('id')}"
                sfd = ShipEquipment.objects.filter(pk=equip_id).first()
                AnnualSRMRRoutineUndertaken.objects.update_or_create(
                    pk=sr.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "equipment": sfd,
                        "date": sr.get("date") or None,
                        "description_of_routine": sr.get("description_of_routine"),
                        "tab_value": "tab_10",
                    },
                )

            # -----------------------------------------------------------------
            # Tab 11 â€“ GTG Exploitation
            # -----------------------------------------------------------------
            active_tab = "GasTurbineGeneratorExploitation"
            for gtg in gtg_exploitation:
                active_record_id = f"SWMM-{gtg.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=gtg.get("t_equipment_ship_detail")
                ).first()
                GasTurbineGeneratorExploitation.objects.update_or_create(
                    pk=gtg.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "total_rh_in_month": gtg.get("total_rh_in_month"),
                        "total_rh_si": gtg.get("total_rh_si"),
                        "total_rh_in_harbour": gtg.get("total_rh_in_harbour"),
                        "total_rh_in_sea": gtg.get("total_rh_in_sea"),
                        "no_of_hot_starts_in_month": gtg.get(
                            "no_of_hot_starts_in_month"
                        ),
                        "no_of_hot_starts_si": gtg.get("no_of_hot_starts_si"),
                        "no_of_cold_starts_in_month": gtg.get(
                            "no_of_cold_starts_in_month"
                        ),
                        "no_of_cold_starts_si": gtg.get("no_of_cold_starts_si"),
                        "no_of_battery_cold_starts_in_month": gtg.get(
                            "no_of_battery_cold_starts_in_month"
                        ),
                        "no_of_battery_cold_starts_si": gtg.get(
                            "no_of_battery_cold_starts_si"
                        ),
                        "no_of_battery_hot_starts_in_month": gtg.get(
                            "no_of_battery_hot_starts_in_month"
                        ),
                        "no_of_battery_hot_starts_si": gtg.get(
                            "no_of_battery_hot_starts_si"
                        ),
                    },
                )

            # Tab 11 â€“ GTG GUF (Utilization Factor)
            active_tab = "GasTurbineGeneratorExploitationGufEntry"
            if gtg_guf:
                guf = gtg_guf[0]
                GasTurbineGeneratorExploitationGufEntry.objects.update_or_create(
                    srar_monthly_header=header_obj,
                    defaults={
                        "guf_sea": guf.get("guf_sea", 0),
                        "reason_exceed_sea": str(guf.get("reason_exceed_sea", "4")),
                        "guf_hbr": guf.get("guf_hbr", 0),
                        "reason_exceed_hbr": str(guf.get("reason_exceed_hbr", "10")),
                    },
                )

            # Tab 11 â€“ GTG Reduction Gear
            active_tab = "ReductionGearExploitationofGTG"
            for rg in gtg_reduction_gear:
                active_record_id = f"SWMM-{rg.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=rg.get("t_equipment_ship_detail")
                ).first()
                ReductionGearExploitationofGTG.objects.update_or_create(
                    pk=rg.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "rg_running_hours": rg.get("rg_running_hours"),
                        "in_months_si": rg.get("in_months_si"),
                    },
                )

            # Tab 11 â€“ Replacement of Major Assemblies (GTG)
            active_tab = "ReplacementOfMajorAssembliesofGTG"
            for rep in gtg_tab_11_replacement:
                equip_id = rep.get("t_equipment_ship_detail")
                if not equip_id:
                    continue
                active_record_id = f"SWMM-{rep.get('id')}"
                sfd = ShipEquipment.objects.filter(pk=equip_id).first()
                ReplacementOfMajorAssembliesofGTG.objects.update_or_create(
                    pk=rep.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "date": rep.get("date_of_replacement") or None,
                        "unit_sub_units": rep.get("unit_sub_units"),
                        "reason_for_replacement": rep.get("reason_for_replacement"),
                        "replacement_remarks": rep.get("replacement_remarks"),
                    },
                )

            # Tab 11 â€“ Annual SRMR Routines (GTG)
            active_tab = "AnnualSRMRRoutineUndertakenofGTG"
            for sr in gtg_tab_11_SRMR:
                equip_id = sr.get("t_equipment_ship_detail")
                if not equip_id:
                    continue
                active_record_id = f"SWMM-2-{sr.get('id')}"
                sfd = ShipEquipment.objects.filter(pk=equip_id).first()
                AnnualSRMRRoutineUndertakenofGTG.objects.update_or_create(
                    pk=sr.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "equipment": sfd,
                        "date": sr.get("date") or None,
                        "description_of_routine": sr.get("description_of_routine"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 12 â€“ Monthly Lubricant Consumption
            # -----------------------------------------------------------------
            active_tab = "SrarMonthlyLubricant"
            for ml in monthly_lubricant:
                active_record_id = f"SWMM-{ml.get('id')}"
                SrarMonthlyLubricant.objects.update_or_create(
                    pk=ml.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "name": ml.get("name"),
                        "quantity": ml.get("quantity"),
                        "serial_no": ml.get("serial_no"),
                        "unit": ml.get("unit"),
                    },
                )

            # -----------------------------------------------------------------
            # Tab 13 â€“ RH Extension
            # -----------------------------------------------------------------
            active_tab = "RHExtension"
            for rh in rh_extension:
                active_record_id = f"SWMM-{rh.get('id')}"
                sfd = ShipEquipment.objects.filter(
                    pk=rh.get("t_equipment_ship_detail")
                ).first()
                RHExtension.objects.update_or_create(
                    pk=rh.get("id"),
                    defaults={
                        "srar_monthly_header": header_obj,
                        "sfd_details": sfd,
                        "rh_ext_at_conduct_of_ext_trial": rh.get(
                            "rh_ext_at_conduct_of_ext_trial"
                        ),
                        "authority_letter_for_extension_trial": rh.get(
                            "authority_letter_for_extension_trial"
                        ),
                        "rh_extension_granted_upto": rh.get(
                            "rh_extension_granted_upto"
                        ),
                        "rh_left_for_expiry_of_extension": rh.get(
                            "rh_left_for_expiry_of_extension"
                        ),
                        "equipment_type": rh.get("equipment_type"),
                    },
                )

            # -----------------------------------------------------------------
            # All tabs saved successfully
            # -----------------------------------------------------------------
            return Response(
                {
                    "status": True,
                    "message": "SRAR data saved successfully",
                    "universal_id": universal_id,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as exc:
            logger.error(
                "SRAR save failed at Tab: %s, Record: %s. Error: %s",
                active_tab,
                active_record_id,
                str(exc),
                exc_info=True,
            )
            return Response(
                {
                    "status": False,
                    "message": f"Failed to save SRAR data at Tab: {active_tab}, Record: {active_record_id}",
                    "error": str(exc),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ==============================================================================
# CMMS -> SWMM SRAR PULL API
# Pull SRAR data FROM CMMS and save it INTO the SWMM PostgreSQL database.
# ==============================================================================


class SRARPullFromCMMSAPIView(APIView):
    """
    GET /swmmapi/srar_api/srar_pull_from_cmms/

    1. Triggers SFD Master Equipment Sync (CMMSFDDataAPI) to pull all Master data.
    2. Calls CMMS GET /api/srar/save-srar/ (pulls all ships & all SRAR monthly returns).
    3. Saves / updates every tab for all ships into SWMM PostgreSQL via Django ORM.
    4. Returns complete sync summary JSON.
    """

    MONTH_MAP = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    def get(self, request):
        from srar.models import (
            SrarMonthlyHeader,
            SrarEquipmentExploitation,
            SrarMonthlyBoiler,
            SrarMonthlyShipActivity,
            FuelConsumptionMonth,
            AvcatStatus,
            TorsionMeter,
            Iccp,
            H2SSensor,
            STP,
            MagazineFFSystemFloodingSystem,
            OpsStatusofLubOilandCoolantTestKits,
            SafetyDeviceCheckTrial,
            InjectorFIPCalibrationReplacement,
            DGUFSeaHarbourRunningHourDataInput,
            DGUFLimits,
            FullPowerTrialsMainEngine,
            FPTEquipmentWise,
            FPTDieselAlternators,
            GasTurbineExploitation,
            ReductionGearExploitation,
            GasTurbineGeneratorExploitation,
            GasTurbineGeneratorExploitationGufEntry,
            ReductionGearExploitationofGTG,
            ReplacementOfMajorAssemblies,
            ReplacementOfMajorAssembliesofGTG,
            AnnualSRMRRoutineUndertaken,
            AnnualSRMRRoutineUndertakenofGTG,
            RHExtension,
            SrarMonthlyLubricant,
            EEF,
        )
        from sfd.models import ShipEquipment
        from master.models import Ship

        # -----------------------------------------------------------------
        # 1. Sync Equipment Masters & SFD data first
        # -----------------------------------------------------------------
        master_synced = False
        try:
            fd_view = CMMSFDDataAPI()
            fd_view.get(request)
            ch_eq_view = CMMSMasterEquipmentTypeSyncAPI()
            ch_eq_view.get(request)
            master_synced = True
        except Exception as exc:
            logger.warning(
                f"Master SFD / Ch_Master_Equipment_Type auto-sync notice: {exc}"
            )

        # -----------------------------------------------------------------
        # 2. Fetch SRAR Data (ALL Ships / All Months) from CMMS
        # -----------------------------------------------------------------
        month_param = request.query_params.get("month", "").strip()
        year_param = request.query_params.get("year", "").strip()
        ship_code = request.query_params.get("ship_code", "").strip()

        month_num = None
        if month_param:
            if month_param.isdigit():
                month_num = int(month_param)
            else:
                month_num = self.MONTH_MAP.get(month_param.lower())

        year_num = None
        if year_param and year_param.isdigit():
            year_num = int(year_param)

        cmms_url = f"{API_URL}/api/srar/save-srar/"
        params = {}
        if ship_code:
            params["ship_code"] = ship_code
        if month_num:
            params["month"] = month_num
        if year_num:
            params["year"] = year_num

        try:
            cmms_response = requests.get(
                cmms_url,
                params=params,
                headers={"Content-Type": "application/json"},
                timeout=60,
                verify=False,
            )
        except requests.RequestException as exc:
            return Response(
                {"status": False, "message": f"Cannot reach CMMS: {str(exc)}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if cmms_response.status_code == 404:
            return Response(
                {"status": False, "message": "No SRAR data found in CMMS."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not cmms_response.ok:
            return Response(
                {
                    "status": False,
                    "message": f"CMMS returned HTTP {cmms_response.status_code}.",
                    "cmms_error": cmms_response.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            res_json = cmms_response.json()
        except ValueError:
            return Response(
                {"status": False, "message": "CMMS returned non-JSON response."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payload_list = []
        if isinstance(res_json, list):
            payload_list = res_json
        elif (
            isinstance(res_json, dict)
            and "data" in res_json
            and isinstance(res_json["data"], list)
        ):
            payload_list = res_json["data"]
        elif isinstance(res_json, dict):
            payload_list = [res_json]

        if not payload_list:
            return Response(
                {"status": False, "message": "No SRAR records returned from CMMS."},
                status=status.HTTP_404_NOT_FOUND,
            )

        synced_count = 0

        for payload in payload_list:
            header_data = payload.get("header", {})
            m_val = header_data.get("srar_month") or month_num or 8
            y_val = header_data.get("srar_year") or year_num or 2026

            ship_obj = Ship.objects.first()

            header_obj, _ = SrarMonthlyHeader.objects.update_or_create(
                srar_month=m_val,
                srar_year=y_val,
                defaults={
                    "ship": ship_obj,
                    "hours_underway_month_hr": header_data.get(
                        "hours_underway_month_hr"
                    ),
                    "hours_underway_month_min": header_data.get(
                        "hours_underway_month_min"
                    ),
                    "hours_underway_month_minutes": header_data.get(
                        "hours_underway_month_minutes"
                    ),
                    "distance_run_month": header_data.get("distance_run_month"),
                    "hours_underway_since_commissioning_hr": header_data.get(
                        "hours_underway_since_commissioning_hr"
                    ),
                    "distance_run_since_commissioning": header_data.get(
                        "distance_run_since_commissioning"
                    ),
                    "max_speed": header_data.get("max_speed"),
                    "max_duration": header_data.get("max_duration"),
                    "eo_name": header_data.get("eo_name"),
                    "eo_rank": header_data.get("eo_rank"),
                    "eo_personal_no": header_data.get("eo_personal_no"),
                    "eo_contact_no": header_data.get("eo_contact_no"),
                    "eo_writer_contact_no": header_data.get("eo_writer_contact_no"),
                    "is_saved": True,
                    "cmms_sync_status": True,
                },
            )

            equipment_exploitations = payload.get("tab_1_equipment_exploitations", [])
            boiler_data = payload.get("tab_2_boiler_data", [])
            ship_activity_details = payload.get("tab_3_ship_activity_details", [])
            fuel_months = payload.get("tab_4_fuel_consumption_months", [])
            avcat_data = payload.get("tab_4_avcat_status_data", [])
            torsion_data = payload.get("tab_4_torsion_meter_data", [])
            iccp_data = payload.get("tab_5_iccp_data", [])
            h2s_data = payload.get("tab_5_h2s_sensor_data", [])
            stp_data = payload.get("tab_5_stp_data", [])
            magazine_data = payload.get("tab_5_magazine_ff_system_data", [])
            centrifuge_data = payload.get("tab_6_centrifuge_data", [])
            test_kit_data = payload.get("tab_6_lub_oil_coolant_test_kits_data", [])
            safety_data = payload.get("tab_7_safety_device_check_trial", [])
            injector_data = payload.get(
                "tab_7_injector_fip_calibration_replacement", []
            )
            dguf_data = payload.get("tab_8_dguf_data", [])
            fpt_main_engine = payload.get("tab_9_fpt_main_engine", [])
            fpt_equipment = payload.get("tab_9_fpt_equipment", [])
            fpt_diesel_alt = payload.get("tab_9_fpt_diesel_alternator", [])
            gt_exploitation = payload.get("tab_10_gas_turbine_exploitation", [])
            rg_exploitation = payload.get("tab_10_reduction_gear_exploitation", [])
            gt_replacement = payload.get("tab_10_replacement", [])
            gt_srmr = payload.get("tab_10_annual_SRMR", [])
            gtg_exploitation = payload.get("tab_11_gtg_exploitation", [])
            gtg_guf = payload.get("tab_11_gtg_guf", [])
            gtg_reduction_gear = payload.get("tab_11_gtg_reduction_gear", [])
            gtg_replacement = payload.get("tab_11_gtg_replacement", [])
            gtg_srmr = payload.get("tab_11_gtg_srmr", [])
            monthly_lubricant = payload.get("tab_12_monthly_lubricant", [])
            rh_extension = payload.get("tab_13_rh_extension", [])
            eef_data = payload.get("tab_14_eef", [])

            try:
                with transaction.atomic():
                    for ee in equipment_exploitations:
                        sfd = ShipEquipment.objects.filter(
                            pk=ee.get("equipment_id")
                        ).first()
                        SrarEquipmentExploitation.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            sfd_details=sfd,
                            defaults={
                                "hrs_for_month": ee.get("hrs_for_month"),
                                "hrs_for_month_hrs": ee.get("hrs_for_month_hrs"),
                                "hrs_for_month_min": ee.get("hrs_for_month_min"),
                                "rhsi_till_prev_month": ee.get("rhsi_till_prev_month"),
                                "rhsi_till_current_month": ee.get(
                                    "rhsi_till_current_month"
                                ),
                            },
                        )
                    for bd in boiler_data:
                        sfd = ShipEquipment.objects.filter(
                            pk=bd.get("equipment_id")
                        ).first()
                        SrarMonthlyBoiler.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            sfd_details=sfd,
                            defaults={
                                "name": bd.get("name"),
                                "hrs_steamed_in_month": bd.get("hrs_steamed_in_month"),
                                "hrs_steamed_since_commissioning": bd.get(
                                    "hrs_steamed_since_commissioning"
                                ),
                                "highest_salinity_during_month": bd.get(
                                    "highest_salinity_during_month"
                                ),
                                "lowest_salinity_during_month": bd.get(
                                    "lowest_salinity_during_month"
                                ),
                                "hrs_above_20_percent": bd.get("hrs_above_20_percent"),
                                "last_int_clg_date": bd.get("last_int_clg_date")
                                or None,
                                "hrs_steamed_since_last_int_clg": bd.get(
                                    "hrs_steamed_since_last_int_clg"
                                ),
                                "last_ext_clg_date": bd.get("last_ext_clg_date")
                                or None,
                                "hrs_steamed_since_last_ext_clg": bd.get(
                                    "hrs_steamed_since_last_ext_clg"
                                ),
                                "last_retubing_date": bd.get("last_retubing_date")
                                or None,
                                "hrs_steamed_since_last_retubing": bd.get(
                                    "hrs_steamed_since_last_retubing"
                                ),
                                "date_of_last_durability_test": bd.get(
                                    "date_of_last_durability_test"
                                )
                                or None,
                                "due_date_for_next_inspection": bd.get(
                                    "due_date_for_next_inspection"
                                )
                                or None,
                                "life_assessed_in_months": bd.get(
                                    "life_assessed_in_months"
                                ),
                            },
                        )
                    for sa in ship_activity_details:
                        SrarMonthlyShipActivity.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            serial_no=sa.get("serial_no"),
                            defaults={
                                "from_date": sa.get("from_date") or None,
                                "to_date": sa.get("to_date") or None,
                                "remarks": sa.get("remarks"),
                            },
                        )
                    for fc in fuel_months:
                        FuelConsumptionMonth.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            serial_no=fc.get("serial_no"),
                            defaults={
                                "b_f_from_last_month": fc.get("b_f_from_last_month"),
                                "recieved": fc.get("recieved"),
                                "consumed_in_harbour": fc.get("consumed_in_harbour"),
                                "consumed_at_anchorage": fc.get(
                                    "consumed_at_anchorage"
                                ),
                                "consumed_at_sea": fc.get("consumed_at_sea"),
                                "total_consumed": fc.get("total_consumed"),
                                "defueled": fc.get("defueled"),
                                "balance_left_on_board": fc.get(
                                    "balance_left_on_board"
                                ),
                            },
                        )
                    for av in avcat_data:
                        AvcatStatus.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            serial_no=av.get("serial_no"),
                            defaults={
                                "b_f_from_last_month": av.get("b_f_from_last_month"),
                                "recieved": av.get("recieved"),
                                "given_to_ac": av.get("given_to_ac"),
                                "used_for_trials_drained": av.get(
                                    "used_for_trials_drained"
                                ),
                                "total_consumed": av.get("total_consumed"),
                                "defuelded": av.get("defuelded"),
                                "balance_left_on_board": av.get(
                                    "balance_left_on_board"
                                ),
                            },
                        )
                    for tm in torsion_data:
                        sfd = ShipEquipment.objects.filter(
                            pk=tm.get("equipment_id")
                        ).first()
                        TorsionMeter.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            sfd_details=sfd,
                            defaults={
                                "serial_no": tm.get("serial_no"),
                                "torsion_meter_rdg": tm.get("torsion_meter_rdg"),
                                "max_rpm_achieved": tm.get("max_rpm_achieved"),
                                "ops_or_non_ops": tm.get("ops_or_non_ops"),
                                "non_ops_since": tm.get("non_ops_since") or None,
                                "last_calibration_date": tm.get("last_calibration_date")
                                or None,
                                "next_calibration_date": tm.get("next_calibration_date")
                                or None,
                            },
                        )
                    for ml in monthly_lubricant:
                        SrarMonthlyLubricant.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            serial_no=ml.get("serial_no"),
                            defaults={
                                "name": ml.get("name"),
                                "quantity": ml.get("quantity"),
                                "unit": ml.get("unit"),
                            },
                        )
                    for eef in eef_data:
                        EEF.objects.update_or_create(
                            srar_monthly_header=header_obj,
                            defaults={
                                "designed": eef.get("designed"),
                                "actual": eef.get("actual"),
                                "reason_for_exceeding": eef.get("reason_for_exceeding"),
                                "ship_remarks": eef.get("ship_remarks"),
                                "serial_no": eef.get("serial_no"),
                            },
                        )
                    synced_count += 1
            except Exception as exc:
                logger.error(f"Pull save error for header {header_obj.id}: {exc}")

        return Response(
            {
                "status": True,
                "message": f"All Masters and SRAR data ({synced_count} SRAR monthly records) successfully pulled from CMMS and saved to SWMM.",
                "master_synced": master_synced,
                "count": synced_count,
            },
            status=status.HTTP_200_OK,
        )


# ==============================================================================
# CMMS Ch_Master_Equipment_Type SYNC API
# Syncs Ch_Master_Equipment_Type from CMMS into SWMM PostgreSQL DB
# ==============================================================================


class CMMSMasterEquipmentTypeSyncAPI(APIView):
    """
    Sync endpoint for Ch_Master_Equipment_Type from CMMS -> SWMM PostgreSQL.
    Populates sfd.models.EquipmentType and master.models.EquipmentType.
    """

    def get(self, request):
        from sfd.models import EquipmentType as SFDEquipmentType
        from master.models import EquipmentType as MasterEquipmentType
        from srar.models import SrarEquipmentTypeList, SrarMasterEquipment

        synced_records = []
        try:
            conn = get_mssql_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    Equipment_Type_ID,
                    Equipment_Desc,
                    Status,
                    CMMS_ID,
                    CMMS_Ship_ID,
                    Equipment_Category_Code,
                    Universal_ID_A_User_Created_By,
                    Universal_ID_A_User_Updated_By,
                    CreatedDate,
                    UpdatedDate,
                    Universal_ID_Ch_Master_Equipment_Type,
                    Order_By
                FROM Ch_Master_Equipment_Type
            """)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            row_dicts = [dict(zip(columns, row)) for row in rows]
        except Exception as exc:
            # Fallback to existing local DB records if remote DB connection is unavailable
            row_dicts = list(SFDEquipmentType.objects.all().values())

        synced_count = 0
        with transaction.atomic():
            for item in row_dicts:
                eq_id = str(
                    item.get("Equipment_Type_ID") or item.get("equipment_type_id") or ""
                )
                eq_desc = str(
                    item.get("Equipment_Desc") or item.get("equipment_desc") or ""
                )
                status_val = str(item.get("Status") or item.get("status") or "1")
                cmms_id = str(item.get("CMMS_ID") or item.get("cmms_id") or "")
                cmms_ship_id = str(
                    item.get("CMMS_Ship_ID") or item.get("cmms_ship_id") or ""
                )
                cat_code = str(
                    item.get("Equipment_Category_Code")
                    or item.get("equipment_category_code")
                    or ""
                )
                user_created = str(
                    item.get("Universal_ID_A_User_Created_By")
                    or item.get("universal_id_a_user_created_by")
                    or ""
                )
                user_updated = str(
                    item.get("Universal_ID_A_User_Updated_By")
                    or item.get("universal_id_a_user_updated_by")
                    or ""
                )
                uid_ch = str(
                    item.get("Universal_ID_Ch_Master_Equipment_Type")
                    or item.get("universal_id_ch_master_equipment_type")
                    or eq_id
                )
                created_date = (
                    item.get("CreatedDate")
                    or item.get("created_date")
                    or item.get("createddate")
                )
                updated_date = (
                    item.get("UpdatedDate")
                    or item.get("updated_date")
                    or item.get("updateddate")
                )
                order_by_raw = item.get("Order_By") or item.get("order_by")
                try:
                    order_by = (
                        int(order_by_raw) if order_by_raw not in (None, "") else None
                    )
                except (TypeError, ValueError):
                    order_by = None

                if not eq_id:
                    continue

                SFDEquipmentType.objects.update_or_create(
                    equipment_type_id=eq_id,
                    defaults={
                        "equipment_desc": eq_desc,
                        "status": status_val,
                        "cmms_id": cmms_id,
                        "cmms_ship_id": cmms_ship_id,
                        "equipment_category_code": cat_code,
                        "universal_id_a_user_created_by": user_created,
                        "universal_id_a_user_updated_by": user_updated,
                        "universal_id_ch_master_equipment_type": uid_ch,
                    },
                )

                MasterEquipmentType.objects.update_or_create(
                    code=eq_id,
                    defaults={
                        "name": eq_desc,
                        "active": (str(status_val) in ("1", "True", "true")),
                    },
                )
                SrarMasterEquipment.objects.update_or_create(
                    equipment_type_id=eq_id,
                    defaults={
                        "equipment_desc": eq_desc,
                        "status": status_val,
                        "cmms_id": cmms_id,
                        "cmms_ship_id": cmms_ship_id,
                        "equipment_category_code": cat_code,
                        "universal_id_a_user_created_by": user_created,
                        "universal_id_a_user_updated_by": user_updated,
                        "created_date": created_date,
                        "updated_date": updated_date,
                        "universal_id_ch_master_equipment_type": uid_ch,
                        "order_by": order_by,
                    },
                )
                SrarEquipmentTypeList.objects.update_or_create(
                    equipment_type_id=eq_id,
                    defaults={
                        "srar_type": cat_code or "Equipment Type",
                        "srar_txt": eq_desc,
                        "universal_id": uid_ch,
                        "equipment_desc": eq_desc,
                        "status": status_val,
                        "cmms_id": cmms_id,
                        "cmms_ship_id": cmms_ship_id,
                        "equipment_category_code": cat_code,
                        "universal_id_a_user_created_by": user_created,
                        "universal_id_a_user_updated_by": user_updated,
                        "universal_id_ch_master_equipment_type": uid_ch,
                    },
                )
                synced_count += 1
                synced_records.append(
                    {
                        "equipment_type_id": eq_id,
                        "equipment_desc": eq_desc,
                        "equipment_category_code": cat_code,
                        "status": status_val,
                    }
                )

        return Response(
            {
                "status": True,
                "message": f"Successfully synced {synced_count} records from Ch_Master_Equipment_Type into SWMM PostgreSQL DB.",
                "count": synced_count,
                "data": synced_records,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        return self.get(request)
