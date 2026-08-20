# flake8: noqa
import argparse
import importlib.util
import os
import sys
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swmm.settings")
django.setup()

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import call_command
from django.db import connection, transaction
from django.db import models as django_models
from django.utils import timezone
from ems.models import (  # noqa: E402
    AddRoutineDetails,
    EquipmentName,
    RoutineDescription,
    SectionName,
    ShipMaster,
    UniqueRoutineName,
)
from master.models import (  # noqa: E402
    ChMasterShipRemarksBy,
    ChMasterSymptoms,
    CoMessage,
    Command,
    Country,
    Department,
    Frequency,
    Group,
    HierarchyForChart,
    MaintenanceOccasionMaster,
    Manufacturer,
    MDeferment,
    MDelay,
    MDiagnostic,
    MemberDetail,
    MEquipment,
    MEstablishment,
    MInability,
    MMaterialOrganizations,
    MRanklist,
    MReason,
    MRefit,
    MRefitCategory,
    MRepair,
    MRepairAgency,
    MRequiredAssistance,
    MSeverity,
    MShipCategory,
    MShipClass,
    MShipCommand,
    MShipOpsAuthority,
    MShipPropulsion,
    OrderDuty,
    OpsMaintenancePeriod,
    OverseeingTeam,
    Propulsion,
    RefitMaintenancePeriod,
    Section,
    Ship,
    ShipCategory,
    ShipRole,
    ShipRoleImage,
    SubDepartment,
    Supplier,
    Unit,
    UnitType,
    UpdateEntry,
)
from master.models import (
    EquipmentType as MasterEquipmentType,
)
from master.models import (
    Generic as MasterGeneric,
)
from obs.models import (  # noqa: E402
    Authority,
    Demand,
    Denomination,
    EquipmentClass,
    Issue,
    NotInCattedItem,
    PostDemand,
    PostSurvey,
    Receive,
    SpareClass,
    Spares,
    SparesMapping,
)

try:
    from refit.models import ABER, Delinquency, RefCompDelinquencyDetail  # noqa: E402
except (ImportError, AttributeError):
    ABER = None
    Delinquency = None
    RefCompDelinquencyDetail = None
from sfd.models import (  # noqa: E402
    Equipment,
    EquipmentCategory,
    EquipmentPolicy,
    EquipmentSpecification,
    EquipmentType,
    Generic,
    GenericSpecification,
    SatelliteUnit,
    ShipEquipment,
    TrialUnit,
)
from sfd.models import (
    Supplier as SfdSupplier,
)
from django.contrib.auth import get_user_model

User = get_user_model()

try:
    from users.models import CustomUserProfile
except (ImportError, AttributeError):
    CustomUserProfile = None

try:
    from users.models import Designation, Rank, Role, RoleMaster, role_hierarchy
except (ImportError, AttributeError):
    Designation = None
    Rank = None
    Role = None
    RoleMaster = None
    role_hierarchy = None

try:
    from master.models import MasterCommand
except (ImportError, AttributeError):
    MasterCommand = None

try:
    from users.models import HRCDFMock
except (ImportError, AttributeError):
    HRCDFMock = None

try:
    from users.models import UserMessage
except (ImportError, AttributeError):
    UserMessage = None

try:
    from users.models import (
        LoginRegistrationImage,
        MasterKnowYourRegulator,
        MasterRegulatorDivision,
        OtherCustomUserProfile,
        UserDepartment,
    )
except (ImportError, AttributeError):
    LoginRegistrationImage = None
    MasterKnowYourRegulator = None
    MasterRegulatorDivision = None
    OtherCustomUserProfile = None
    UserDepartment = None

try:
    from crew_manage.models import (
        ActionStationMaster,
        AddressDetails,
        CivilianOfficial,
        CruisingStationMaster,
        DefenceStationMaster,
        EmergencyStationMaster,
        GXForm,
        LeaveApplication,
        LeaveApprovalHistory,
        LeaveApprovalWorkflow,
        LeaveDetails,
        LtcDays,
        MedicalCategory,
        ModeOfTravel,
        PassageType,
        PersonnelAssignment,
        PersonnelStatusLog,
        PlaceOfTyDuty,
        Railway,
        RationType,
        Sailing,
        SailingPersonnel,
        SailorRankClassification,
        ShelterStationMaster,
        TemporaryDuty,
        TemporaryDutyApprovalHistory,
        TemporaryDutyApprovalWorkflow,
        TypeOfLeave,
        TypeOfTempDuty,
    )
except (ImportError, AttributeError):
    ActionStationMaster = None
    AddressDetails = None
    CivilianOfficial = None
    CruisingStationMaster = None
    DefenceStationMaster = None
    EmergencyStationMaster = None
    GXForm = None
    LeaveApplication = None
    LeaveApprovalHistory = None
    LeaveApprovalWorkflow = None
    LeaveDetails = None
    LtcDays = None
    MedicalCategory = None
    ModeOfTravel = None
    PassageType = None
    PersonnelAssignment = None
    PersonnelStatusLog = None
    PlaceOfTyDuty = None
    Railway = None
    RationType = None
    Sailing = None
    SailingPersonnel = None
    SailorRankClassification = None
    ShelterStationMaster = None
    TemporaryDuty = None
    TemporaryDutyApprovalHistory = None
    TemporaryDutyApprovalWorkflow = None
    TypeOfLeave = None
    TypeOfTempDuty = None

try:
    from hotwork.models import AddHotwork, HotworkHODApproval, HotworkProgressActivity
except (ImportError, AttributeError):
    AddHotwork = None
    HotworkHODApproval = None
    HotworkProgressActivity = None

try:
    from inout_tag.models import TagIn, TagInApproval, TagOut
except (ImportError, AttributeError):
    TagIn = None
    TagInApproval = None
    TagOut = None

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_IMAGES = (
    BASE_DIR / ".." / ".." / "frontend" / "public" / "assests" / "images"
).resolve()

SYSTEM_IP = "127.0.0.1"
SEED_PASS = "12345"
SHIP_IMAGE = "ship-img.png"
PROFILE_IMAGE = ""
SEED_SFD_DEMO_DATA = False
GALLERY_IMAGES = [
    "slider-gallery/shipslider1.png",
    "slider-gallery/shipslider2.png",
    "slider-gallery/shipslider3.png",
    "slider-gallery/shipslider4.png",
    "slider-gallery/shipslider5.png",
    "slider-gallery/shipslider6.png",
]

PROJECT_APP_LABELS = {
    "activity_planner",
    "dart",
    "crew_manage",
    "dl_monitor",
    "dms",
    "ems",
    "hotwork",
    "ilms",
    "inout_tag",
    "master",
    "obs",
    "refit",
    # SFD demo seeding is disabled temporarily so CMMS sync data can be verified
    # without generated demo SFD rows mixed into the same tables.
    # "sfd",
    "srar",
    "tank",
    "ticket_manage",
    "users",
    "wlms",
    "work_manage",
}

NAVY_WORDS = [
    "Aster",
    "Varuna",
    "Samudra",
    "Pratap",
    "Nishant",
    "Trident",
    "Vikram",
    "Tarang",
    "Prabal",
    "Sagar",
    "Shakti",
    "Veer",
    "Uday",
    "Kavach",
    "Tejas",
    "Dhruv",
    "Sankalp",
    "Ajeya",
    "Nirbhay",
    "Sarthak",
]

EQUIPMENT_WORDS = [
    "Main Gas Turbine",
    "Diesel Generator",
    "Fire Pump",
    "Steering Gear",
    "Air Compressor",
    "Sea Water Pump",
    "Fresh Water Pump",
    "Main Switchboard",
    "Navigation Radar",
    "Lube Oil Purifier",
    "Fuel Transfer Pump",
    "Sewage Treatment Plant",
]


def image_ref(relative_path):
    path = FRONTEND_IMAGES / relative_path
    if not path.exists():
        print(f"  Warning: frontend image missing: {path}")
    db_path = f"../frontend/public/assests/images/{relative_path}".replace("\\", "/")
    if len(db_path) > 100:
        return relative_path.replace("\\", "/")
    return db_path


def filter_dict_for_model(model, d):
    if not d or not table_exists(model):
        return d or {}
    cols = table_columns(model)
    if not cols:
        return d
    filtered = {}
    for k, v in d.items():
        base = k.split("__")[0]
        try:
            field = model._meta.get_field(base)
            col = getattr(field, "column", base)
            if col in cols:
                filtered[k] = v
        except Exception:
            filtered[k] = v
    return filtered


def upsert(model, lookup, defaults=None):
    defaults = defaults or {}
    safe_lookup = filter_dict_for_model(model, lookup)
    safe_defaults = filter_dict_for_model(model, defaults)
    try:
        obj, created = model.objects.update_or_create(
            **safe_lookup, defaults=safe_defaults
        )
        return obj
    except MultipleObjectsReturned:
        obj = model.objects.filter(**safe_lookup).order_by("pk").first()
        for field_name, value in safe_defaults.items():
            try:
                setattr(obj, field_name, value)
            except Exception:
                pass
        try:
            obj.save()
        except Exception:
            pass
        return obj


def release_conflicting_personnel_number(username, personnel_number):
    if not CustomUserProfile:
        return
    conflicting_profile = (
        CustomUserProfile.objects.filter(personal_number=personnel_number)
        .exclude(customuser__username=username)
        .order_by("pk")
        .first()
    )
    if not conflicting_profile:
        return

    legacy_personal_number = f"L{conflicting_profile.pk:05d}{personnel_number[-4:]}"[
        :15
    ]
    if conflicting_profile.personal_number != legacy_personal_number:
        conflicting_profile.personal_number = legacy_personal_number
        conflicting_profile.save(update_fields=["personal_number"])


def table_exists(model):
    if not model:
        return False
    return model._meta.db_table in connection.introspection.table_names()


def table_columns(model):
    if not model:
        return set()
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, model._meta.db_table
            )
        }


def bind_field_to_existing_column(model, field_name, legacy_column):
    if not table_exists(model):
        return

    field = model._meta.get_field(field_name)
    columns = table_columns(model)
    if field.column in columns or legacy_column not in columns:
        return

    field.db_column = legacy_column
    field.column = legacy_column
    print(
        f"  Using legacy DB column {model._meta.db_table}.{legacy_column} "
        f"for {model.__name__}.{field_name}"
    )


def apply_legacy_dart_seed_column_compatibility():
    bind_field_to_existing_column(
        apps.get_model("dart", "InitiateDart"),
        "severity_code",
        "serverity_code_id",
    )
    bind_field_to_existing_column(
        apps.get_model("dart", "DartSpare"),
        "spare_id",
        "spare_id_id",
    )
    bind_field_to_existing_column(
        apps.get_model("dart", "TempDartSpare"),
        "spare_id",
        "spare_id_id",
    )

    for model in apps.get_models():
        if not table_exists(model):
            continue
        try:
            cols = table_columns(model)
            if not cols:
                continue
            new_local_concrete = [
                f
                for f in model._meta.local_concrete_fields
                if hasattr(f, "column") and f.column and f.column in cols
            ]
            model._meta.local_concrete_fields = tuple(new_local_concrete)

            new_concrete = [
                f
                for f in model._meta.concrete_fields
                if hasattr(f, "column") and f.column and f.column in cols
            ]
            model._meta.concrete_fields = tuple(new_concrete)
        except Exception:
            pass


def is_project_model(model):
    return model._meta.app_label in PROJECT_APP_LABELS and table_exists(model)


def project_models():
    return [model for model in apps.get_models() if is_project_model(model)]


def dependency_sorted_models(models):
    model_set = set(models)
    sorted_models = []
    visiting = set()
    visited = set()

    def visit(model):
        if model in visited:
            return
        if model in visiting:
            return
        visiting.add(model)
        for field in model._meta.get_fields():
            if (
                getattr(field, "concrete", False)
                and getattr(field, "is_relation", False)
                and getattr(field, "related_model", None) in model_set
                and field.related_model is not model
            ):
                visit(field.related_model)
        visiting.remove(model)
        visited.add(model)
        sorted_models.append(model)

    for model in models:
        visit(model)
    return sorted_models


def base_defaults(user=None):
    profile = getattr(user, "user_profile", user) if user else None
    return {
        "created_by": profile,
        "modified_by": profile,
        "created_ip": SYSTEM_IP,
        "modified_ip": SYSTEM_IP,
        "active": 1,
    }


def clear_seeded_data():
    with connection.cursor() as cursor:
        names = [
            f'"{model._meta.db_table}"'
            for model in project_models()
            if not model._meta.auto_created
        ]
        if names:
            cursor.execute(
                f"TRUNCATE TABLE {', '.join(names)} RESTART IDENTITY CASCADE;"
            )
    print("Cleared project database tables.")


def ensure_seed_system_user():
    profile = None
    if CustomUserProfile:
        profile, _ = CustomUserProfile.objects.update_or_create(
            personal_number="PN0001",
            defaults={
                "firstname": "System",
                "lastname": "Administrator",
                "designation": "Commanding Officer",
                "access_level": "0",
                "has_credentials": True,
                "user_active": True,
                "remarks": "SWMM seed account",
            },
        )
    user_defaults = {
        "password": make_password(SEED_PASS),
        "is_active": True,
        "is_admin": True,
    }
    if profile:
        user_defaults["user_profile"] = profile

    user = upsert(
        User,
        {"username": "1234"},
        user_defaults,
    )
    user.set_password(SEED_PASS)
    user.save()
    return user


def seed_masters():
    now = timezone.now()
    system_user = ensure_seed_system_user()
    departments = {}
    for code, name, description in [
        ("ME", "Marine Engineering", "Main propulsion, auxiliaries, hull systems"),
        (
            "EE",
            "Electrical Engineering",
            "Power generation and electrical distribution",
        ),
        ("WE", "Weapons and Electronics", "Sensors, weapons and combat systems"),
        ("OPS", "Operations", "Navigation, communications and operational readiness"),
        ("LOG", "Logistics", "Stores, victualling and supply chain"),
    ]:
        departments[code] = upsert(
            Department,
            {"code": code},
            {
                "name": name,
                "dep_code": code,
                "description": description,
                "sfd_applicable": 1,
                **base_defaults(system_user),
            },
        )

    commands = {}
    for command_id, code, name in [
        (1, "WNC", "Western Naval Command"),
        (2, "ENC", "Eastern Naval Command"),
        (3, "SNC", "Southern Naval Command"),
    ]:
        commands[code] = upsert(
            MShipCommand,
            {"command_id": command_id},
            {
                "command_code": code,
                "command_name": name,
                "command_ref": code,
                "active": True,
                "created_date": now,
                "updated_date": now,
            },
        )
        upsert(
            Command,
            {"command_name": name},
            {"unit_name": code, **base_defaults(system_user)},
        )

    master_commands = {}
    if MasterCommand and table_exists(MasterCommand):
        for code, name in [
            ("WNC", "Western Naval Command"),
            ("ENC", "Eastern Naval Command"),
            ("SNC", "Southern Naval Command"),
        ]:
            master_commands[code] = upsert(
                MasterCommand,
                {"unit_name": code},
                {"command_name": name},
            )

    roles = {}
    if Role and table_exists(Role):
        for idx, r_name in enumerate(
            ["SHIPADMIN", "CO", "HOD", "DyHOD", "Storekeeper", "Maintainer"], 1
        ):
            roles[r_name] = upsert(Role, {"role_name": r_name}, {})
            if RoleMaster and table_exists(RoleMaster):
                upsert(RoleMaster, {"role_name": r_name}, {})
            if role_hierarchy and table_exists(role_hierarchy):
                upsert(role_hierarchy, {"role_name": r_name}, {"id": idx})

    designations = {}
    if Designation and table_exists(Designation):
        for d_name in [
            "Commanding Officer",
            "Head of Department",
            "Deputy HOD",
            "Admin Officer",
            "Maintainer",
            "Storekeeper",
        ]:
            designations[d_name] = upsert(Designation, {"designation_name": d_name}, {})

    ranks = {}
    if Rank and table_exists(Rank):
        for r_name, dept_code in [
            ("Captain", "OPS"),
            ("Commander", "ME"),
            ("Lieutenant Commander", "EE"),
            ("Lieutenant", "OPS"),
            ("Chief Petty Officer", "ME"),
            ("Petty Officer", "LOG"),
        ]:
            ranks[r_name] = upsert(
                Rank,
                {"name": r_name},
                {"department": departments.get(dept_code)},
            )

    categories = {}
    for category_id, name, order in [
        (1, "Destroyer", 1),
        (2, "Frigate", 2),
        (3, "Corvette", 3),
        (4, "Fleet Support Ship", 4),
        (5, "Survey Vessel", 5),
        (6, "Aircraft Carrier", 6),
        (7, "Mine Countermeasure", 7),
    ]:
        categories[name] = upsert(
            MShipCategory,
            {"ship_category_id": category_id},
            {
                "ship_category_name": name,
                "ar_report_order": order,
                "active": True,
                "created_date": now,
                "updated_date": now,
            },
        )
        upsert(
            ShipCategory,
            {"code": f"SC{category_id:02d}"},
            {"name": name, **base_defaults(system_user)},
        )

    classes = {}
    for class_id, code, description in [
        (1, "VAYU", "Vayu class guided missile destroyer"),
        (2, "TARANG", "Tarang class stealth frigate"),
        (3, "SAGAR", "Sagar class offshore patrol vessel"),
        (4, "PRABAL", "Prabal class fleet support ship"),
        (5, "VIKRAM", "Vikram class aircraft carrier"),
    ]:
        classes[code] = upsert(
            MShipClass,
            {"class_id": class_id},
            {
                "class_code": code,
                "description": description,
                "hull_code": code[:3],
                "active": True,
                "created_date": now,
                "updated_date": now,
            },
        )

    propulsion = {}
    for propulsion_id, name in [
        (1, "Gas Turbine COGAG"),
        (2, "Combined Diesel and Gas"),
        (3, "Diesel Electric"),
        (4, "Integrated Electric Propulsion"),
    ]:
        propulsion[name] = upsert(
            MShipPropulsion,
            {"propulsion_id": propulsion_id},
            {
                "propulsion_name": name,
                "active": True,
                "created_date": now,
                "updated_date": now,
            },
        )
        upsert(Propulsion, {"name": name}, base_defaults(system_user))

    authorities = {}
    for authority_id, code, name, command_code in [
        (1, "FOCWF", "Flag Officer Commanding Western Fleet", "WNC"),
        (2, "FOCEF", "Flag Officer Commanding Eastern Fleet", "ENC"),
        (3, "FOCS", "Flag Officer Commanding Southern Naval Area", "SNC"),
    ]:
        authorities[code] = upsert(
            MShipOpsAuthority,
            {"authority_id": authority_id},
            {
                "ops_code": code,
                "ops_authority": name,
                "command": commands[command_code],
                "command_name": commands[command_code].command_name,
                "active": True,
                "created_date": now,
                "updated_date": now,
                "address": f"{name}, Naval Headquarters",
            },
        )

    country = upsert(
        Country,
        {"code": "IN"},
        {"name": "India", **base_defaults(system_user)},
    )
    unit_type = upsert(
        UnitType,
        {"name": "Surface Combatant"},
        base_defaults(system_user),
    )
    overseeing_team = upsert(
        OverseeingTeam,
        {"code": "FST"},
        {"name": "Fleet Support Team", **base_defaults(system_user)},
    )
    unit = upsert(
        Unit,
        {"code": "FLT"},
        {
            "name": "Fleet Unit",
            "description": "Operational fleet unit",
            **base_defaults(system_user),
        },
    )

    sections = {}
    for code, name, dept in [
        ("ME-MP", "Main Propulsion", "ME"),
        ("ME-AUX", "Auxiliary Machinery", "ME"),
        ("EE-PWR", "Power Generation", "EE"),
        ("WE-RDR", "Radar and Sensors", "WE"),
        ("OPS-NAV", "Navigation", "OPS"),
    ]:
        sections[code] = upsert(
            Section,
            {"code": code},
            {
                "name": name,
                "department": departments[dept],
                **base_defaults(system_user),
            },
        )

    generic = upsert(
        MasterGeneric,
        {"code": "GEN-MAR"},
        {"sr_no": "1", "type": "Marine Equipment", **base_defaults(system_user)},
    )
    group = upsert(
        Group,
        {"code": "GRP-MACH"},
        {
            "name": "Machinery Group",
            "section": sections["ME-MP"],
            "generic": generic,
            **base_defaults(system_user),
        },
    )
    master_eq_type = upsert(
        MasterEquipmentType,
        {"code": "TYPE-MAIN"},
        {"name": "Main Machinery", **base_defaults(system_user)},
    )
    supplier = upsert(
        Supplier,
        {"code": "SUP-NDY"},
        {
            "name": "Naval Dockyard Stores",
            "address": "Naval Dockyard",
            "area_street": "Dockyard Road",
            "city": "Mumbai",
            "country": country,
            "supplier_manufacture": "Naval",
            "contact_person": "Stores Officer",
            "contact_number": "+91 90000 10000",
            "email_id": "stores@navy.local",
            **base_defaults(system_user),
        },
    )
    manufacturer = upsert(
        Manufacturer,
        {"code": "MFR-BDL"},
        {
            "name": "Bharat Defence Engineering",
            "country": country,
            "city": "Mumbai",
            "contact_person": "Service Liaison",
            "contact_number": "+91 90000 20000",
            "email": "support@bde.local",
            **base_defaults(system_user),
        },
    )

    for rankid, rank in [
        (1, "Captain"),
        (2, "Commander"),
        (3, "Lieutenant Commander"),
        (4, "Chief Petty Officer"),
        (5, "Petty Officer"),
    ]:
        upsert(MRanklist, {"rankid": rankid}, {"rankdescription": rank, "active": True})

    for model, rows, id_field, name_field in [
        (
            MSeverity,
            [
                (1, "CAT", "Catastrophic"),
                (2, "CRI", "Critical"),
                (3, "MAJ", "Major"),
                (4, "MIN", "Minor"),
            ],
            "severity_id",
            "severity_name",
        ),
        (
            MDelay,
            [
                (1, "SP", "Spares Awaited"),
                (2, "OEM", "OEM Assistance Awaited"),
                (3, "DY", "Dockyard Capacity"),
            ],
            "delay_id",
            "delay_name",
        ),
        (
            MRepairAgency,
            [
                (1, "SS", "Ship Staff"),
                (2, "ND", "Naval Dockyard"),
                (3, "OEM", "OEM Representative"),
            ],
            "repair_agency_id",
            "repair_agency_name",
        ),
        (
            MRepair,
            [
                (1, "REP", "Component Replacement"),
                (2, "OH", "System Overhaul"),
                (3, "CAL", "Calibration"),
            ],
            "repair_id",
            "repair_name",
        ),
        (
            MDiagnostic,
            [
                (1, "VIB", "Vibration Analysis"),
                (2, "IR", "Insulation Resistance Test"),
                (3, "LOP", "Lube Oil Pressure Check"),
            ],
            "diagnostic_id",
            "diagnostic_name",
        ),
    ]:
        model.objects.all().delete()
        code_field = id_field.replace("_id", "_code")
        for row_id, code, name in rows:
            upsert(
                model,
                {"id": row_id},
                {
                    id_field: row_id,
                    code_field: code,
                    name_field: name,
                    "active": 1,
                    "created_date": now,
                    "updated_date": now,
                },
            )

    for inability_id, code, description in [
        (1, "FI", "Full inability"),
        (2, "PI", "Partial inability"),
        (3, "NI", "No inability"),
    ]:
        upsert(
            MInability,
            {"inability_id": inability_id},
            {"inability_code": code, "description": description, "active": True},
        )
    for reason_id, code, description in [
        (1, "MF", "Material failure"),
        (2, "OP", "Operational commitment"),
        (3, "WX", "Weather window"),
    ]:
        upsert(
            MReason,
            {"reason_id": reason_id},
            {"reason_code": code, "description": description, "active": True},
        )
    for deferment_id, code, description in [
        (1, "D-SR", "Deferred to short refit"),
        (2, "D-NR", "Deferred to normal refit"),
    ]:
        upsert(
            MDeferment,
            {"deferment_id": deferment_id},
            {"deferment_code": code, "description": description, "active": True},
        )
    for mo_id, name in [
        (1, "Material Organisation Mumbai"),
        (2, "Material Organisation Visakhapatnam"),
    ]:
        upsert(
            MMaterialOrganizations,
            {"mo_id": mo_id},
            {"mo_name": name, "created_date": now, "updated_date": now},
        )
    for est_id, name in [
        (1, "Naval Dockyard Mumbai"),
        (2, "Naval Dockyard Visakhapatnam"),
    ]:
        upsert(MEstablishment, {"est_id": est_id}, {"est_name": name, "active": True})

    for category_id, name in [
        (1, "Short Refit"),
        (2, "Normal Refit"),
        (3, "Medium Refit"),
    ]:
        upsert(
            MRefitCategory,
            {"refit_category_id": category_id},
            {"refit_category_name": name, "active": True},
        )
    refit_category = MRefitCategory.objects.get(refit_category_id=1)
    for refit_id, code, description in [
        (1, "SR", "Short Refit"),
        (2, "NR", "Normal Refit"),
        (3, "MR", "Medium Refit"),
    ]:
        upsert(
            MRefit,
            {"refit_id": refit_id},
            {
                "refit_type": code,
                "description": description,
                "refit_category_f_key": refit_category,
                "refit_category_id": refit_category.refit_category_id,
                "active": True,
            },
        )

    for frequency_id, name, prefix, months in [
        (1, "Daily", "D", 0),
        (2, "Weekly", "W", 0),
        (3, "Monthly", "M", 1),
        (4, "Quarterly", "Q", 3),
        (5, "Annual", "A", 12),
    ]:
        upsert(
            Frequency,
            {"frequency_id": frequency_id},
            {
                "frequency": name,
                "frequency_prefix": prefix,
                "months": months,
                "active": True,
            },
        )

    ChMasterShipRemarksBy.objects.all().delete()
    for code, text in [(1, "SS"), (2, "OTHER THAN SS (DYD,FMU,TRADE,ETC.)")]:
        upsert(
            ChMasterShipRemarksBy,
            {"id": code},
            {"ship_remark_by_id": code, "description": text, "active": 1},
        )
    ChMasterSymptoms.objects.all().delete()
    for symptom_id, code in [
        (1, "High vibration"),
        (2, "Low lube oil pressure"),
        (3, "Sea water leak"),
        (4, "IR low"),
    ]:
        upsert(
            ChMasterSymptoms,
            {"id": symptom_id},
            {
                "symptom_id": symptom_id,
                "symptom_code": code,
                "active": 1,
                "department": departments["ME"],
            },
        )
    MRequiredAssistance.objects.all().delete()
    for assistance_id, code, text in [
        (1, "DY", "Dockyard assistance"),
        (2, "OEM", "OEM assistance"),
        (3, "FST", "Fleet support team"),
    ]:
        upsert(
            MRequiredAssistance,
            {"required_assistance_id": assistance_id},
            {
                "required_assistance_code": code,
                "required_assistance_for": text,
                "active": True,
            },
        )

    return {
        "departments": departments,
        "commands": commands,
        "master_commands": master_commands,
        "roles": roles,
        "designations": designations,
        "ranks": ranks,
        "categories": categories,
        "classes": classes,
        "propulsion": propulsion,
        "authorities": authorities,
        "country": country,
        "unit_type": unit_type,
        "overseeing_team": overseeing_team,
        "unit": unit,
        "sections": sections,
        "generic": generic,
        "group": group,
        "master_eq_type": master_eq_type,
        "supplier": supplier,
        "manufacturer": manufacturer,
    }


def seed_ships(ctx):
    specs = [
        (
            "INS Rama",
            "IA01",
            "Destroyer",
            "VAYU",
            "WNC",
            "FOCWF",
            "Gas Turbine COGAG",
            "163",
            "7200",
            "29",
            "6400",
        ),
        (
            "INS Varuna",
            "IV02",
            "Frigate",
            "TARANG",
            "ENC",
            "FOCEF",
            "Combined Diesel and Gas",
            "145",
            "5600",
            "28",
            "5200",
        ),
        (
            "INS Samudra",
            "IS03",
            "Corvette",
            "SAGAR",
            "ENC",
            "FOCEF",
            "Diesel Electric",
            "112",
            "3200",
            "24",
            "4300",
        ),
        (
            "INS Pratap",
            "IP04",
            "Fleet Support Ship",
            "PRABAL",
            "WNC",
            "FOCWF",
            "Integrated Electric Propulsion",
            "196",
            "18500",
            "21",
            "9800",
        ),
        (
            "INS Nishant",
            "IN05",
            "Survey Vessel",
            "SAGAR",
            "SNC",
            "FOCS",
            "Diesel Electric",
            "98",
            "2600",
            "20",
            "3600",
        ),
        (
            "INS Nilgiri",
            "IN06",
            "Frigate",
            "TARANG",
            "WNC",
            "FOCWF",
            "Combined Diesel and Gas",
            "149",
            "6600",
            "28",
            "5500",
        ),
        (
            "INS Kolkata",
            "IK07",
            "Destroyer",
            "VAYU",
            "WNC",
            "FOCWF",
            "Gas Turbine COGAG",
            "163",
            "7500",
            "30",
            "8000",
        ),
        (
            "INS Vikrant",
            "IV08",
            "Aircraft Carrier",
            "VIKRAM",
            "SNC",
            "FOCS",
            "Gas Turbine COGAG",
            "262",
            "45000",
            "28",
            "7500",
        ),
        (
            "INS Mahe",
            "IM09",
            "Mine Countermeasure",
            "SAGAR",
            "WNC",
            "FOCWF",
            "Diesel Electric",
            "60",
            "900",
            "15",
            "2500",
        ),
        (
            "INS Vipul",
            "IV10",
            "Corvette",
            "PRABAL",
            "WNC",
            "FOCWF",
            "Diesel Electric",
            "91",
            "1450",
            "25",
            "4000",
        ),
        (
            "INS Nashak",
            "IN11",
            "Corvette",
            "PRABAL",
            "WNC",
            "FOCWF",
            "Diesel Electric",
            "91",
            "1450",
            "25",
            "4000",
        ),
    ]
    ships = []
    for index, (
        name,
        code,
        category,
        ship_class,
        command,
        authority,
        propulsion,
        length,
        displacement,
        speed,
        range_nm,
    ) in enumerate(specs, 1):
        ship = upsert(
            Ship,
            {"code": code},
            {
                "ship_external_id": 1000 + index,
                "sr_no": str(index),
                "name": name,
                "ship_image": "master/ship_image/ship-img.png",
                "ship_description": f"{name} is an imaginary Indian Navy {category.lower()}"
                + "configured for SWMM demonstrations.",
                "ship_role_description": "Maritime security, fleet escort, machinery readiness"
                + "and operational support.",
                "ship_category": ctx["categories"][category],
                "class_master": ctx["classes"][ship_class],
                "class_code": ship_class,
                "commission_date": date(2018 + index, min(index, 12), 15),
                "command": ctx["commands"][command],
                "authority": ctx["authorities"][authority],
                "ops_code": authority,
                "ship_builder": "Naval Design Bureau",
                "displacement": f"{displacement} tonnes",
                "hours_underway": str(900 + index * 125),
                "distance_run": range_nm,
                "propulsion": ctx["propulsion"][propulsion],
                "sdrsref": f"SDRS-{code}",
                "active_external": True,
                "yard_no": f"Y-{200 + index}",
                "classification_society": "Naval Classification Cell",
                "length_overall": length,
                "engine_rating": f"{45000 + index * 7000} hp",
                "max_cont_speed": speed,
                "eco_speed": "14",
                "endurance": f"{range_nm} nm",
                "refit_authority": "Naval Dockyard",
                "signal_name": code,
                "address": f"{name}, Fleet Mail Office",
                "contact_number": f"+91 90000 30{index:03d}",
                "nud_email_id": f"{code.lower()}@navy.local",
                "nic_email_id": f"{code.lower()}@nic.local",
                "is_cmms_install": True,
                "is_in_gd": True,
                "unit_type": ctx["unit_type"],
                "overseeing_team": ctx["overseeing_team"],
                "ship_category_string": category,
                "class_master_string": ship_class,
                "unit_type_string": ctx["unit_type"].name,
                "propulsion_string": propulsion,
                "overseeing_team_string": "240",
                "command_string": ctx["commands"][command].command_name,
                "authority_string": ctx["authorities"][authority].ops_authority,
                "customer_code": code,
                **base_defaults(ensure_seed_system_user()),
            },
        )
        ships.append(ship)
        upsert(ShipMaster, {"ship_name": name}, {})
    return ships


def seed_users(ctx, ships):
    ship_nilgiri = next((s for s in ships if "NILGIRI" in s.name.upper()), ships[0])
    ship_kolkata = next((s for s in ships if "KOLKATA" in s.name.upper()), ships[0])
    ship_vikrant = next((s for s in ships if "VIKRANT" in s.name.upper()), ships[0])
    ship_mahe = next((s for s in ships if "MAHE" in s.name.upper()), ships[0])
    ship_vipul = next((s for s in ships if "VIPUL" in s.name.upper()), ships[0])
    ship_nashak = next(
        (s for s in ships if "NASHAK" in s.name.upper() or "NASHK" in s.name.upper()),
        ships[0],
    )

    users = [
        (
            "1234",
            "System",
            "Administrator",
            "Captain",
            "Commanding Officer",
            "OPS",
            "SHIPADMIN",
            "WNC",
            ships[0],
            "0",
            True,
        ),
        (
            "shipadmin",
            "Ship",
            "Admin",
            "Captain",
            "Commanding Officer",
            "OPS",
            "SHIPADMIN",
            "WNC",
            ships[0],
            "0",
            True,
        ),
        (
            "co",
            "Commanding",
            "Officer",
            "Captain",
            "Commanding Officer",
            "OPS",
            "CO",
            "WNC",
            ships[0],
            "0",
            True,
        ),
        (
            "DyHOD",
            "Vikram",
            "Rao",
            "Lieutenant Commander",
            "Deputy HOD",
            "EE",
            "DyHOD",
            "WNC",
            ships[0],
            "1",
            True,
        ),
        (
            "Admin",
            "Neha",
            "Singh",
            "Lieutenant",
            "Admin Officer",
            "OPS",
            "SHIPADMIN",
            "ENC",
            ships[1],
            "0",
            True,
        ),
        (
            "Maintainer",
            "Rohan",
            "Kapoor",
            "Chief Petty Officer",
            "Maintainer",
            "ME",
            "Maintainer",
            "SNC",
            ships[2],
            "2",
            True,
        ),
        (
            "Storekeeper",
            "Karan",
            "Nair",
            "Petty Officer",
            "Storekeeper",
            "LOG",
            "Storekeeper",
            "WNC",
            ships[3],
            "2",
            True,
        ),
        # INS NILGIRI
        (
            "UA_INS_NILGIRI",
            "Unit",
            "Admin Nilgiri",
            "Lieutenant",
            "Admin Officer",
            "OPS",
            "SHIPADMIN",
            "WNC",
            ship_nilgiri,
            "1",
            False,
        ),
        # INS KOLKATA
        (
            "UA_INS_KOLKATA",
            "Unit",
            "Admin Kolkata",
            "Lieutenant",
            "Admin Officer",
            "OPS",
            "SHIPADMIN",
            "WNC",
            ship_kolkata,
            "1",
            False,
        ),
        (
            "INS_KA",
            "Kolkata",
            "Admin",
            "Lieutenant",
            "Admin Officer",
            "OPS",
            "SHIPADMIN",
            "WNC",
            ship_kolkata,
            "1",
            False,
        ),
        (
            "LO_WRITER_INS_KOLKATA",
            "LO",
            "Writer Kolkata",
            "Petty Officer",
            "Writer",
            "LOG",
            "Storekeeper",
            "WNC",
            ship_kolkata,
            "2",
            False,
        ),
        (
            "HOD_WRITER_INS_KOLKATA",
            "HOD",
            "Writer Kolkata",
            "Chief Petty Officer",
            "Writer",
            "ME",
            "Maintainer",
            "WNC",
            ship_kolkata,
            "2",
            False,
        ),
        (
            "LO_INS_KOLKATA",
            "Logistics",
            "Officer Kolkata",
            "Lieutenant",
            "Admin Officer",
            "LOG",
            "SHIPADMIN",
            "WNC",
            ship_kolkata,
            "1",
            False,
        ),
        (
            "HOD_INS_KOLKATA",
            "HOD",
            "Officer Kolkata",
            "Commander",
            "HOD",
            "ME",
            "SHIPADMIN",
            "WNC",
            ship_kolkata,
            "1",
            False,
        ),
        # INS VIKRANT
        (
            "VIKRANT_U2",
            "Vikrant",
            "User 2",
            "Lieutenant Commander",
            "Maintainer",
            "ME",
            "Maintainer",
            "SNC",
            ship_vikrant,
            "2",
            False,
        ),
        (
            "VIKRANT_U1",
            "Vikrant",
            "User 1",
            "Lieutenant",
            "Maintainer",
            "ME",
            "Maintainer",
            "SNC",
            ship_vikrant,
            "2",
            False,
        ),
        # INS MAHE
        (
            "MAHE_U2",
            "Mahe",
            "User 2",
            "Lieutenant Commander",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_mahe,
            "2",
            False,
        ),
        (
            "MAHE_U1",
            "Mahe",
            "User 1",
            "Lieutenant",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_mahe,
            "2",
            False,
        ),
        # INS VIPUL
        (
            "VIPUL_U2",
            "Vipul",
            "User 2",
            "Lieutenant Commander",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_vipul,
            "2",
            False,
        ),
        (
            "VIPUL_U1",
            "Vipul",
            "User 1",
            "Lieutenant",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_vipul,
            "2",
            False,
        ),
        # INS NASHAK
        (
            "NASHK_U2",
            "Nashak",
            "User 2",
            "Lieutenant Commander",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_nashak,
            "2",
            False,
        ),
        (
            "NASHK_USER1",
            "Nashak",
            "User 1",
            "Lieutenant",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_nashak,
            "2",
            False,
        ),
        (
            "NASHK_U1",
            "Nashak",
            "User 1 Sub",
            "Lieutenant",
            "Maintainer",
            "ME",
            "Maintainer",
            "WNC",
            ship_nashak,
            "2",
            False,
        ),
    ]

    created = {}

    for index, (
        raw_username,
        first,
        last,
        rank_name,
        designation_name,
        dept_code,
        role_code,
        cmd_code,
        ship,
        access_level,
        is_staff,
    ) in enumerate(users, 1):
        username = raw_username.upper()

        profile = None

        if CustomUserProfile and table_exists(CustomUserProfile):
            personal_number = f"PN{index:04d}"

            profile = CustomUserProfile.objects.filter(
                personal_number=personal_number
            ).first()
            if not profile:
                profile = CustomUserProfile.objects.create(
                    personal_number=personal_number,
                    firstname=first,
                    lastname=last,
                    has_credentials=True,
                    user_active=True,
                    access_level=access_level,
                )
            else:
                profile.firstname = first
                profile.lastname = last
                profile.has_credentials = True
                profile.user_active = True
                profile.access_level = access_level
                profile.save()

        user_defaults = {
            "is_active": True,
            "is_admin": raw_username
            in (
                "1234",
                "shipadmin",
                "co",
            )
            or is_staff,
        }

        if profile:
            user_defaults["user_profile"] = profile

        user = User.objects.filter(username__iexact=username).first()
        if not user:
            user = User.objects.create(
                username=username,
                **user_defaults,
            )
        else:
            for k, v in user_defaults.items():
                setattr(user, k, v)
            user.save()

        admin_pass_users = {
            "UA_INS_NILGIRI",
            "UA_INS_KOLKATA",
            "INS_KA",
            "LO_WRITER_INS_KOLKATA",
            "HOD_WRITER_INS_KOLKATA",
            "LO_INS_KOLKATA",
            "HOD_INS_KOLKATA",
            "VIKRANT_U2",
            "VIKRANT_U1",
            "MAHE_U2",
            "MAHE_U1",
            "VIPUL_U2",
            "VIPUL_U1",
            "NASHK_U2",
            "NASHK_USER1",
            "NASHK_U1",
        }
        is_admin_pass = username in admin_pass_users or raw_username in admin_pass_users
        user.set_password("admin" if is_admin_pass else SEED_PASS)
        user.save()

        created[username] = user
        created[raw_username] = user
        created[raw_username.upper()] = user
        created[raw_username.lower()] = user

        print(f"Created user: {username}")

    return created


def seed_users_extra(ctx, users):
    """Seed the users-app models that seed_users()/seed_masters() don't already cover."""
    admin_profile = getattr(users["1234"], "user_profile", users["1234"])
    dyhod_profile = getattr(users["DyHOD"], "user_profile", users["DyHOD"])

    if UserDepartment and table_exists(UserDepartment):
        for name in [
            "Marine Engineering",
            "Electrical Engineering",
            "Weapons and Electronics",
            "Operations",
            "Logistics",
        ]:
            upsert(UserDepartment, {"name": name}, {})

    other_profile = None
    if OtherCustomUserProfile and table_exists(OtherCustomUserProfile):
        other_profile = upsert(
            OtherCustomUserProfile,
            {"personal_number": "OTH0001"},
            {
                "firstname": "Sanjay",
                "lastname": "Verma",
                "rank": ctx.get("ranks", {}).get("Lieutenant"),
                "department": ctx["departments"]["OPS"],
                "designation": "Liaison Officer",
                "section": "OPS-SEC",
                "access_level": "3",
                "created_by": admin_profile,
            },
        )

    division = None
    if MasterRegulatorDivision and table_exists(MasterRegulatorDivision):
        division = upsert(
            MasterRegulatorDivision,
            {"regulator": dyhod_profile, "division": "Engine Room Division"},
            {"department": ctx["departments"]["ME"]},
        )

    if MasterKnowYourRegulator and table_exists(MasterKnowYourRegulator):
        maintainer_profile = getattr(
            users["Maintainer"], "user_profile", users["Maintainer"]
        )
        upsert(
            MasterKnowYourRegulator,
            {"regulator": dyhod_profile, "department": ctx["departments"]["ME"]},
            {"sailor": maintainer_profile, "division": division},
        )

    if LoginRegistrationImage and table_exists(LoginRegistrationImage):
        upsert(
            LoginRegistrationImage,
            {"name": "SWMM Login Banner"},
            {
                "image": image_ref(SHIP_IMAGE),
                "source": "login-registration-image",
                "uploaded_by": admin_profile,
                "is_active": True,
            },
        )

    return {"other_profile": other_profile, "division": division}


def seed_landing(users, ships):
    CoMessage.objects.update_or_create(
        id=1,
        defaults={
            "message": "Maintain material readiness, report defects early and keep every system fit for sea.",
            "valid_till_date": date.today() + timedelta(days=90),
        },
    )
    ShipRole.objects.update_or_create(
        id=1,
        defaults={
            "role_title": "Know Your Ship",
            "current_text": "The ship is a self-contained fighting unit where engineering, logistics,"
            + "operations and command teams work together to keep the platform ready for sea.",
        },
    )
    ship_role = ShipRole.objects.get(id=1)
    for idx, image in enumerate([SHIP_IMAGE] + GALLERY_IMAGES[:2], 1):
        ShipRoleImage.objects.update_or_create(
            id=idx,
            defaults={"ship": ship_role, "image": image_ref(image)},
        )

    for idx, (name, designation, rank) in enumerate(
        [
            ("Capt System Administrator", "Commanding Officer", "Captain"),
            ("Cdr Arjun Mehra", "Head of Department", "Commander"),
            ("LCdr Vikram Rao", "Deputy Head of Department", "Lieutenant Commander"),
        ],
        1,
    ):
        MemberDetail.objects.update_or_create(
            id=idx,
            defaults={
                "name": name,
                "designation": designation,
                "rank": rank,
                "image_path": image_ref(PROFILE_IMAGE),
            },
        )

    UpdateEntry.objects.update_or_create(
        id=1,
        defaults={
            "from_date": date.today(),
            "to_date": date.today() + timedelta(days=7),
            "update_text": "Weekly machinery trials and preservation rounds planned for all departments.",
        },
    )

    for offset, filename, description, officer_details, routine_details in [
        (
            0,
            "daily_order_today.pdf",
            "Daily operational order covering harbour routines, safety rounds and readiness checks.",
            "Duty Officer: Lt Arjun Mehra; Executive Officer: Cdr Vikram Rao",
            "0800 harbour rounds; 1000 machinery readiness checks; 1600 evening quarters",
        ),
        (
            1,
            "daily_order_tomorrow.pdf",
            "Daily operational order for scheduled sea-training preparation and department coordination.",
            "Duty Officer: Lt Neha Singh; Engineering Duty Officer: Lt Cdr Rohan Nair",
            "0730 physical training; 0930 pre-sailing checks; 1500 damage-control drill",
        ),
        (
            2,
            "daily_order_maintenance_day.pdf",
            "Daily operational order for planned maintenance, preservation and logistics activities.",
            "Duty Officer: Lt Karan Kapoor; Logistics Officer: Lt Cdr Vikram Rao",
            "0800 maintenance conference; 1100 preservation rounds; 1700 stores review",
        ),
    ]:
        order_date = date.today() + timedelta(days=offset)
        upsert(
            OrderDuty,
            {"filename": filename},
            {
                "source": "daily order",
                "pdf_path": f"master/order_duty/{filename}",
                "from_date": order_date,
                "to_date": order_date,
                "date": order_date,
                "description": description,
                "officer_details": officer_details,
                "routine_details": routine_details,
            },
        )

    for offset, officer_name, rank in [
        (0, "Arjun Mehra", "Lt"),
        (1, "Neha Singh", "Lt"),
        (2, "Rohan Nair", "Lt Cdr"),
        (3, "Karan Kapoor", "Lt"),
        (4, "Vikram Rao", "Cdr"),
    ]:
        roster_date = date.today() + timedelta(days=offset)
        filename = f"duty_roster_ood_{roster_date.isoformat()}.pdf"
        upsert(
            OrderDuty,
            {"filename": filename},
            {
                "source": "duty roster",
                "pdf_path": f"master/order_duty/{filename}",
                "roster_name": f"Officer of the Day - {roster_date:%d %b %Y}",
                "from_date": roster_date,
                "to_date": roster_date,
                "date": roster_date,
                "description": f"Officer of the Day duty roster for {roster_date:%d %B %Y}.",
                "officer_details": f"Officer of the Day: {rank} {officer_name}",
                "routine_details": "Assume duty at 0800; conduct rounds; report readiness state at 1800.",
            },
        )

    admin_profile = getattr(users["1234"], "user_profile", users["1234"])
    dyhod_profile = getattr(users["DyHOD"], "user_profile", users["DyHOD"])

    co = HierarchyForChart.objects.update_or_create(
        id=1,
        defaults={
            "node_type": "co",
            "user": admin_profile,
            "photo": image_ref(PROFILE_IMAGE),
            "is_commander_officer": True,
        },
    )[0]
    engineering = HierarchyForChart.objects.update_or_create(
        id=2,
        defaults={
            "node_type": "division",
            "division_name": "Engineering Department",
            "parent": co,
        },
    )[0]
    HierarchyForChart.objects.update_or_create(
        id=3,
        defaults={
            "node_type": "user",
            "user": None,
            "parent": engineering,
            "is_regulator": True,
        },
    )
    HierarchyForChart.objects.update_or_create(
        id=4,
        defaults={"node_type": "user", "user": dyhod_profile, "parent": engineering},
    )


def seed_equipment_and_work(ctx, users, ships):
    admin_profile = getattr(users["1234"], "user_profile", users["1234"])
    section_name = upsert(
        SectionName,
        {"name": "Main Propulsion"},
        {"department": ctx["departments"]["ME"]},
    )
    sub_department = upsert(
        SubDepartment,
        {"name": "Gas Turbine Room"},
        {
            "department_name": ctx["departments"]["ME"],
            "description": "Main propulsion machinery spaces",
        },
    )
    generic_spec = upsert(GenericSpecification, {"name": "Main Propulsion"}, {})
    generic = upsert(Generic, {"code": "GT"}, {"specification": generic_spec})
    eq_spec = upsert(EquipmentSpecification, {"name": "Naval Gas Turbine"}, {})
    policy = upsert(
        EquipmentPolicy,
        {"policy": "Condition Based Maintenance"},
        {"directive": "Inspect during every harbour maintenance window."},
    )
    sfd_supplier = upsert(
        SfdSupplier,
        {"SupplierCode": "SFD-NDY"},
        {"SupplierName": "Naval Dockyard Stores", "City": "Mumbai", "active": "Y"},
    )
    trial_unit = upsert(
        TrialUnit,
        {"code": "TR-ME"},
        {
            "name": "Machinery Trial Unit",
            "description": "Propulsion trials",
            "sequence": 1,
            "status": 1,
            "created_by": admin_profile,
        },
    )
    satellite = upsert(
        SatelliteUnit,
        {"code": "SAT-ME"},
        {
            "trial_unit": trial_unit,
            "name": "Propulsion Satellite Unit",
            "description": "Machinery satellite unit",
            "sequence": 1,
            "status": 1,
            "created_by": admin_profile,
        },
    )
    category = upsert(
        EquipmentCategory,
        {"name": "Main Propulsion"},
        {
            "trial_unit": trial_unit,
            "satellite_unit": satellite,
            "ship": ships[0],
            "description": "Main propulsion equipment",
        },
    )
    sfd_type = upsert(
        EquipmentType,
        {"equipment_type_id": "GT"},
        {"equipment_desc": "Gas Turbine", "status": "ACTIVE", "order_by": 1},
    )

    master_equipment = upsert(
        MEquipment,
        {"code": "ME-GT-001"},
        {
            "name": "Main Gas Turbine",
            "country": ctx["country"],
            "group": ctx["group"],
            "model": "BDE-GT-25000",
            "manufacturer": ctx["manufacturer"],
            "supplier": ctx["supplier"],
            "obsolete": "NO",
            "authority": "Naval Headquarters",
            "generic_code": "GT",
            "ilms_equipment_code": "ILMS-GT-001",
            "maintop_number": "MTP/GT/001",
            "type": ctx["master_eq_type"],
            **base_defaults(users["1234"]),
        },
    )

    sfd_equipment = upsert(
        Equipment,
        {"equipment_code": "EQ-GT-001"},
        {
            "ilms_eq_code": "ILMS-GT-001",
            "equipment_class": "Propulsion",
            "model": "BDE-GT-25000",
            "maintop_number": "MTP/GT/001",
            "generic_specification": generic_spec,
            "generic": generic,
            "specification": eq_spec,
            "policy": policy,
        },
    )
    ship_equipment = upsert(
        ShipEquipment,
        {"t_equipment_ship_detail": "TESD-001"},
        {
            "ship": ships[0],
            "supplier": sfd_supplier,
            "equipment_category": category,
            "satelite_unit": satellite,
            "trial_unit": trial_unit,
            "department": ctx["departments"]["ME"],
            "equipment": sfd_equipment,
            "equipment_type_f_key": sfd_type,
            "sub_department_f_key": sub_department,
            "section_f_key": ctx["sections"]["ME-MP"],
            "status": "active",
            "equipment_serial_no": "GT-SN-1001",
            "nomenclature": "MAIN GAS TURBINE",
            "location_code": "2-120-1",
            "location_on_board": "Main Machinery Compartment",
            "compartment": "MMR-1",
            "deck": "2 Deck",
            "installation_date": date(2021, 4, 10),
            "no_of_fits": 1,
            "service_life": "12000 RH",
            "authority_installation": "NHQ/ME/GT/2021",
            "quantity": 1,
            "rshi": "850",
            "eq_rhsi": "850",
            "eqp_specs": "Marine gas turbine driving starboard shaft.",
            "is_synced": True,
        },
    )

    equipment_name = upsert(
        EquipmentName,
        {"equipment_code": "EQ-GT-001"},
        {
            "name": "MAIN GAS TURBINE",
            "nomenclature": "MAIN GAS TURBINE",
            "extra": "Starboard shaft",
            "section": section_name,
            "sub_department": sub_department,
            "rhsi": 850,
            "state": "ACTIVE",
            "started_at_location": "AT SEA",
            "sfd_equipment": ship_equipment,
        },
    )
    routine_name = upsert(
        UniqueRoutineName, {"name": "CHECK GAS TURBINE LUBE OIL PRESSURE"}, {}
    )
    frequency = Frequency.objects.get(frequency_id=3)
    routine = upsert(
        AddRoutineDetails,
        {"routine_no": "ME/GT/M01"},
        {
            "class_name": ships[0].class_code,
            "ship": ShipMaster.objects.get(ship_name=ships[0].name),
            "equipment_name": equipment_name,
            "equipment_code": "EQ-GT-001",
            "nomenclature": "MAIN GAS TURBINE",
            "maintop_no": "MTP/GT/001",
            "routine_name": routine_name,
            "by_whom": "Ship Staff",
            "frequency_in_months": 1,
            "rhs_i": "850",
            "frequency": "Monthly",
            "frequency_f_key": frequency,
            "routine_category": "CALENDAR BASED",
            "remarks": "Seeded monthly propulsion routine.",
        },
    )
    weekly_routine_descriptions = [
        "Record lube oil pressure and inspect filter bowls.",
        "Verify gas turbine vibration readings within limits.",
        "Check enclosure ventilation and clean intake screens.",
        "Inspect fuel supply line joints for leakage.",
        "Test local alarm indication and log readings.",
    ]
    routine_descriptions = []
    for idx, description in enumerate(weekly_routine_descriptions, start=1):
        routine_descriptions.append(
            upsert(
                RoutineDescription,
                {"routine_no": f"ME/GT/M01-{chr(64 + idx)}"},
                {
                    "equipment_name": equipment_name,
                    "routine_name": routine_name,
                    "add_routine_details": routine,
                    "maintop_no": "MTP/GT/001",
                    "routine_description": description,
                    "by_whom": "Ship Staff",
                    # Set due_date in the past to guarantee it is overdue
                    "due_date": date.today() - timedelta(days=7 + idx),
                    "previous_completed_date": date.today() - timedelta(days=20),
                    "department_f_key": ctx["departments"]["ME"],
                    "is_close": False,
                    "is_greater_than_3_monthly": False,
                },
            )
        )
    routine_description = routine_descriptions[0]

    # Seed additional overdue routines for other test departments (EE, OPS) to support their users
    custom_routines_data = [
        {
            "dept_code": "EE",
            "section_name": "Power Generation",
            "sub_dept_name": "Generator Room",
            "sub_dept_desc": "Electrical power generation space",
            "eq_code": "EQ-GEN-002",
            "eq_name": "MAIN DIESEL GENERATOR",
            "eq_nomenclature": "MAIN DIESEL GENERATOR",
            "eq_extra": "No. 1 Generator",
            "routine_no": "EE/GEN/M01",
            "maintop_no": "MTP/GEN/001",
            "routine_name_val": "CHECK DIESEL GENERATOR PARAMETERS",
            "sub_routines": [
                "Verify generator output parameters and insulation levels.",
                "Inspect generator bearings and clean stator winding filters.",
            ],
        },
        {
            "dept_code": "OPS",
            "section_name": "Navigation",
            "sub_dept_name": "Bridge",
            "sub_dept_desc": "Navigation and bridge operations space",
            "eq_code": "EQ-NAV-003",
            "eq_name": "NAVIGATION RADAR",
            "eq_nomenclature": "NAVIGATION RADAR",
            "eq_extra": "Main Bridge Radar",
            "routine_no": "OPS/NAV/M01",
            "maintop_no": "MTP/NAV/001",
            "routine_name_val": "CHECK NAVIGATION RADAR OPERATION",
            "sub_routines": [
                "Clean radar scanner unit and test bridge display response.",
                "Measure magnetron current and verify transceiver sensitivity.",
            ],
        },
    ]

    for cdata in custom_routines_data:
        dept_obj = ctx["departments"][cdata["dept_code"]]
        c_sec_name = upsert(
            SectionName,
            {"name": cdata["section_name"]},
            {"department": dept_obj},
        )
        c_sub_dept = upsert(
            SubDepartment,
            {"name": cdata["sub_dept_name"]},
            {
                "department_name": dept_obj,
                "description": cdata["sub_dept_desc"],
            },
        )
        c_eq_name = upsert(
            EquipmentName,
            {"equipment_code": cdata["eq_code"]},
            {
                "name": cdata["eq_name"],
                "nomenclature": cdata["eq_nomenclature"],
                "extra": cdata["eq_extra"],
                "section": c_sec_name,
                "sub_department": c_sub_dept,
                "rhsi": 850,
                "state": "ACTIVE",
                "started_at_location": "AT SEA",
            },
        )
        c_rt_name = upsert(UniqueRoutineName, {"name": cdata["routine_name_val"]}, {})
        c_routine = upsert(
            AddRoutineDetails,
            {"routine_no": cdata["routine_no"]},
            {
                "class_name": ships[0].class_code,
                "ship": ShipMaster.objects.get(ship_name=ships[0].name),
                "equipment_name": c_eq_name,
                "equipment_code": cdata["eq_code"],
                "nomenclature": cdata["eq_nomenclature"],
                "maintop_no": cdata["maintop_no"],
                "routine_name": c_rt_name,
                "by_whom": "Ship Staff",
                "frequency_in_months": 1,
                "rhs_i": "850",
                "frequency": "Monthly",
                "frequency_f_key": frequency,
                "routine_category": "CALENDAR BASED",
                "remarks": f"Seeded monthly {cdata['eq_name'].lower()} routine.",
            },
        )
        for s_idx, s_desc in enumerate(cdata["sub_routines"], start=1):
            upsert(
                RoutineDescription,
                {"routine_no": f"{cdata['routine_no']}-{chr(64 + s_idx)}"},
                {
                    "equipment_name": c_eq_name,
                    "routine_name": c_rt_name,
                    "add_routine_details": c_routine,
                    "maintop_no": cdata["maintop_no"],
                    "routine_description": s_desc,
                    "by_whom": "Ship Staff",
                    # Guaranteed overdue: set to a past date
                    "due_date": date.today() - timedelta(days=7 + s_idx),
                    "previous_completed_date": date.today() - timedelta(days=20),
                    "department_f_key": dept_obj,
                    "is_close": False,
                    "is_greater_than_3_monthly": False,
                },
            )

    spare_class = upsert(
        SpareClass, {"name": "PROPULSION", "department": ctx["departments"]["ME"]}, {}
    )
    equipment_class = upsert(
        EquipmentClass, {"name": "GAS TURBINE", "spare_class": spare_class}, {}
    )
    denomination = upsert(
        Denomination, {"name": "NOS", "department": ctx["departments"]["ME"]}, {}
    )
    authority = upsert(Authority, {"name": "NAVAL HQ"}, {})
    spare = upsert(
        Spares,
        {"pattern_number": "GT-FLTR-001"},
        {
            "equipment_class": equipment_class,
            "description": "LUBE OIL FILTER ELEMENT",
            "category": Spares.CONSUMABLE,
            "critical": True,
            "compartment": "MMR-1",
            "location": "STORE ROOM",
            "rack_position": "A1",
            "rack_number": "R1",
            "denomination": denomination,
            "quantity_authorised": 12,
            "quantity_available": 10,
            "authority": authority,
            "page": "P-12",
            "line": "4",
            "remarks": "CRITICAL PROPULSION SPARE",
            "image": image_ref(SHIP_IMAGE),
        },
    )
    if not Issue.objects.filter(spare=spare, dart_number="DART-SEED-001").exists():
        Issue.objects.create(
            spare=spare,
            equipment=equipment_name,
            username=getattr(users["Maintainer"], "user_profile", users["Maintainer"]),
            quantity_issued=1,
            remarks="Issued for monthly lube oil routine",
            dart_number="DART-SEED-001",
        )

    initiate_dart_model = apps.get_model("dart", "InitiateDart")
    complete_defect_model = apps.get_model("dart", "CompleteDefectDart")
    completed_routine_model = apps.get_model("dart", "CompletedRoutine")
    dart_spare_model = apps.get_model("dart", "DartSpare")

    dart_seed_rows = [
        {
            "number": "DART-DASH-001",
            "component": "MAIN GAS TURBINE",
            "description": "Spares required for repair. Indent raised.",
            "trial": True,
            "closed": True,
            "spares": True,
            "days_delay": 3,
            "routine_hours": 90,
            "manpower": 120,
            "date_offset": -150,
            "dart_occasion": "AMP",
            "maintenance_period": "OPERATIONAL",
        },
        {
            "number": "DART-DASH-002",
            "component": "MAIN GAS TURBINE",
            "description": "Technical inspection completed. Defect confirmed.",
            "trial": True,
            "closed": False,
            "spares": False,
            "days_delay": 5,
            "routine_hours": 80,
            "manpower": 100,
            "date_offset": -120,
            "dart_occasion": "SMP",
            "maintenance_period": "OPERATIONAL",
        },
        {
            "number": "DART-DASH-003",
            "component": "FIRE PUMP 003",
            "description": "Pump vibration reported during machinery trial.",
            "trial": True,
            "closed": True,
            "spares": True,
            "days_delay": 4,
            "routine_hours": 75,
            "manpower": 90,
            "date_offset": -90,
            "dart_occasion": "DL II",
            "maintenance_period": "REFIT",
        },
        {
            "number": "DART-DASH-004",
            "component": "FIRE PUMP 003",
            "description": "Seal leakage observed during harbour checks.",
            "trial": False,
            "closed": False,
            "spares": True,
            "days_delay": 0,
            "routine_hours": 65,
            "manpower": 70,
            "date_offset": -60,
            "dart_occasion": "DL III",
            "maintenance_period": "REFIT",
        },
        {
            "number": "DART-DASH-005",
            "component": "HYDRAULIC FILTER ELEMENT",
            "description": "Filter clogging indication repeated after routine run.",
            "trial": True,
            "closed": True,
            "spares": False,
            "days_delay": 2,
            "routine_hours": 110,
            "manpower": 40,
            "date_offset": -30,
            "dart_occasion": "HARBOUR",
            "maintenance_period": "OPERATIONAL",
        },
        {
            "number": "DART-DASH-006",
            "component": "MAIN SWITCHBOARD",
            "description": "Intermittent breaker trip observed during load trial.",
            "trial": True,
            "closed": False,
            "spares": False,
            "days_delay": 0,
            "routine_hours": 55,
            "manpower": 60,
            "date_offset": -15,
            "dart_occasion": "DL III",
            "maintenance_period": "REFIT",
        },
        {
            "number": "DART-DASH-007",
            "component": "AIR COMPRESSOR",
            "description": "Pressure drop observed during operational checks.",
            "trial": False,
            "closed": False,
            "spares": True,
            "days_delay": 0,
            "routine_hours": 45,
            "manpower": 50,
            "date_offset": -7,
            "dart_occasion": "OP",
            "maintenance_period": "OPERATIONAL",
        },
    ]

    for index, row in enumerate(dart_seed_rows, start=1):
        dart_date = date.today() + timedelta(days=row["date_offset"])
        dart = upsert(
            initiate_dart_model,
            {"dart_number": row["number"]},
            {
                "equipment_ship": ship_equipment,
                "equipment_ems": equipment_name,
                "department_id": ctx["departments"]["ME"],
                "dart_date": dart_date,
                "rectification_date": dart_date + timedelta(days=7),
                "defective_component": row["component"],
                "defective_discriptions": row["description"],
                "trial_required": row["trial"],
                "sapres_required": row["spares"],
                "is_closed": row["closed"],
                "dart_occasion": row["dart_occasion"],
                "maintenance_period": row["maintenance_period"],
            },
        )
        if row["closed"]:
            upsert(
                complete_defect_model,
                {"serial_no": f"CD-{index:03d}", "dart_details": dart},
                {
                    "dart_no": row["number"],
                    "rectified_date": dart_date + timedelta(days=row["days_delay"]),
                    "days_delay": row["days_delay"],
                    "spares_delay": 0,
                    "lesson_learnt": "Seeded dashboard closure record.",
                },
            )
        upsert(
            completed_routine_model,
            {"old_dart_number": row["number"]},
            {
                "routine": routine_description,
                "new_dart_number": f"ROUTINE-{index:03d}",
                "date_of_completion": dart_date + timedelta(days=2),
                "hours": row["routine_hours"],
                "minutes": 0,
                "carried_by": "Ship Staff",
                "p_no": (
                    users["Maintainer"].user_profile.personal_number
                    if users["Maintainer"].user_profile
                    else "PN0001"
                ),
                "total_manpower": row["manpower"],
                "completion_details": row["description"],
                "trial_team": row["trial"],
            },
        )
        if row["spares"]:
            upsert(
                dart_spare_model,
                {"dart": dart, "pattern": f"DSP-{index:03d}"},
                {
                    "spare_id": spare.id,
                    "equipment_id": ship_equipment,
                    "inventory_type": "OBS",
                    "description": row["description"],
                    "quantity": index,
                    "is_delete": False,
                },
            )

    inventory_systems = [
        {
            "department": "ME",
            "class_name": "FUEL TRANSFER SYSTEM",
            "equipment_name": "FUEL TRANSFER PUMP",
            "pattern": "FUEL-PUMP-ASSY-001",
            "description": "FUEL PUMP ASSEMBLY",
            "category": Spares.RETURNABLE,
            "critical": True,
            "authorised": 5,
            "available": 2,
            "demand_qty": 2,
            "receive_qty": 2,
            "post_demand": True,
            "survey": True,
        },
        {
            "department": "ME",
            "class_name": "HYDRAULIC SYSTEM",
            "equipment_name": "HYDRAULIC POWER PACK",
            "pattern": "HYD-FLTR-ELEM-002",
            "description": "HYDRAULIC FILTER ELEMENT",
            "category": Spares.CONSUMABLE,
            "critical": False,
            "authorised": 10,
            "available": 0,
            "demand_qty": 4,
            "receive_qty": 3,
            "post_demand": True,
            "survey": False,
        },
        {
            "department": "WE",
            "class_name": "WEAPON INTERFACE SYSTEM",
            "equipment_name": "MISSILE INTERFACE UNIT",
            "pattern": "MIS-INT-KIT-003",
            "description": "MISSILE INTERFACE KIT",
            "category": Spares.RETURNABLE,
            "critical": True,
            "authorised": 4,
            "available": 1,
            "demand_qty": 1,
            "receive_qty": 1,
            "post_demand": False,
            "survey": True,
        },
        {
            "department": "EE",
            "class_name": "SERVO CONTROL SYSTEM",
            "equipment_name": "SERVO MOTOR UNIT",
            "pattern": "SERVO-MOTOR-004",
            "description": "SERVO MOTOR UNIT",
            "category": Spares.RETURNABLE,
            "critical": False,
            "authorised": 6,
            "available": 6,
            "demand_qty": 0,
            "receive_qty": 0,
            "post_demand": False,
            "survey": False,
        },
        {
            "department": "ME",
            "class_name": "TEST EQUIPMENT",
            "equipment_name": "PRESSURE TEST KIT",
            "pattern": "PRESS-TEST-KIT-005",
            "description": "PRESSURE TEST KIT",
            "category": Spares.PERMANENT,
            "critical": False,
            "authorised": 2,
            "available": 2,
            "demand_qty": 0,
            "receive_qty": 0,
            "post_demand": False,
            "survey": False,
        },
    ]

    for index, item in enumerate(inventory_systems, start=1):
        department = ctx["departments"][item["department"]]
        class_name = item["class_name"]
        system_spare_class = upsert(
            SpareClass,
            {"name": class_name, "department": department},
            {},
        )
        system_equipment_class = upsert(
            EquipmentClass,
            {"name": class_name, "spare_class": system_spare_class},
            {},
        )
        system_spare = upsert(
            Spares,
            {"pattern_number": item["pattern"]},
            {
                "equipment_class": system_equipment_class,
                "description": item["description"],
                "category": item["category"],
                "critical": item["critical"],
                "compartment": f"MMR-{(index % 3) + 1}",
                "location": "MAIN STORE",
                "rack_position": f"B{index}",
                "rack_number": f"R{index + 10}",
                "denomination": denomination,
                "quantity_authorised": item["authorised"],
                "quantity_available": item["available"],
                "authority": authority,
                "page": f"INV-{index}",
                "line": str(index),
                "remarks": "SHIP INVENTORY DASHBOARD SEED",
                "mo_demand_number": f"MO-DEMAND-{index:03d}",
                "image": image_ref(SHIP_IMAGE),
                "is_obs": True,
            },
        )
        system_ship_equipment = upsert(
            ShipEquipment,
            {"t_equipment_ship_detail": f"INV-SYS-{index:03d}"},
            {
                "ship": ships[0],
                "supplier": sfd_supplier,
                "equipment_category": category,
                "satelite_unit": satellite,
                "trial_unit": trial_unit,
                "department": department,
                "equipment": sfd_equipment,
                "equipment_type_f_key": sfd_type,
                "sub_department_f_key": sub_department,
                "section_f_key": ctx["sections"].get(
                    f"{item['department']}-MP",
                    ctx["sections"]["ME-MP"],
                ),
                "status": "active",
                "equipment_serial_no": f"INV-SN-{index:04d}",
                "nomenclature": item["equipment_name"],
                "location_code": f"2-12{index}-1",
                "location_on_board": "Main Machinery Compartment",
                "compartment": f"MMR-{(index % 3) + 1}",
                "deck": "2 Deck",
                "installation_date": date(2021, 4, 10),
                "no_of_fits": 1,
                "service_life": "12000 RH",
                "authority_installation": f"NHQ/INV/{index:03d}",
                "quantity": 1,
                "rshi": str(850 + index),
                "eq_rhsi": str(850 + index),
                "eqp_specs": f"{item['equipment_name']} supportability seed.",
                "is_synced": True,
            },
        )
        upsert(
            SparesMapping,
            {
                "equipment_class": system_equipment_class,
                "equipment": system_ship_equipment,
            },
            {"section_name": ctx["sections"].get("ME-MP")},
        )

        if item["demand_qty"]:
            demand = upsert(
                Demand,
                {"spare": system_spare, "dart_number": f"DMD-SEED-{index:03d}"},
                {"quantity_todemand": item["demand_qty"]},
            )
            if item["post_demand"]:
                upsert(
                    PostDemand,
                    {"demand_number": f"DMD-SEED-{index:03d}"},
                    {
                        "spare": system_spare,
                        "quantity_demanded": item["demand_qty"],
                        "demand_date": timezone.now(),
                        "remarks": "SHIP INVENTORY DASHBOARD SEED",
                        "created_by": users["Storekeeper"].username,
                        "created_by_user": users["Storekeeper"],
                        "dart_number": demand.dart_number,
                    },
                )
        if item["receive_qty"]:
            Receive.objects.update_or_create(
                spare=system_spare,
                dart_number=f"RCV-SEED-{index:03d}",
                defaults={"quantity_toreceive": item["receive_qty"]},
            )
        if item["survey"]:
            upsert(
                PostSurvey,
                {"spare": system_spare, "survey_number": f"SRV-SEED-{index:03d}"},
                {
                    "quantity_surveyed": 1,
                    "survey_type": PostSurvey.OPDEM,
                    "survey_report_date": timezone.now(),
                    "remarks": "REPAIR CYCLE DASHBOARD SEED",
                    "has_pts": False,
                    "created_by": users["Storekeeper"].username,
                    "created_by_user": users["Storekeeper"],
                    "dart_number": f"DART-SEED-{index:03d}",
                },
            )
        if index == 3:
            upsert(
                NotInCattedItem,
                {"spare_id": system_spare},
                {"incatted_status": False, "is_deleted": False},
            )

    monthly_inventory_issues = [
        (date(2026, 1, 15), "SERVO-MOTOR-004", 32, "REPAIRABLE"),
        (date(2026, 1, 18), "GT-FLTR-001", 56, "CRITICAL"),
        (date(2026, 1, 21), "HYD-FLTR-ELEM-002", 72, "CONSUMABLE"),
        (date(2026, 2, 12), "SERVO-MOTOR-004", 98, "REPAIRABLE"),
        (date(2026, 2, 18), "GT-FLTR-001", 10, "CRITICAL"),
        (date(2026, 2, 22), "HYD-FLTR-ELEM-002", 50, "CONSUMABLE"),
        (date(2026, 3, 10), "SERVO-MOTOR-004", 52, "REPAIRABLE"),
        (date(2026, 3, 16), "GT-FLTR-001", 50, "CRITICAL"),
        (date(2026, 3, 24), "HYD-FLTR-ELEM-002", 94, "CONSUMABLE"),
        (date(2026, 4, 9), "SERVO-MOTOR-004", 68, "REPAIRABLE"),
        (date(2026, 4, 14), "GT-FLTR-001", 62, "CRITICAL"),
        (date(2026, 4, 25), "HYD-FLTR-ELEM-002", 36, "CONSUMABLE"),
        (date(2026, 5, 8), "SERVO-MOTOR-004", 50, "REPAIRABLE"),
        (date(2026, 5, 17), "GT-FLTR-001", 88, "CRITICAL"),
        (date(2026, 5, 27), "HYD-FLTR-ELEM-002", 42, "CONSUMABLE"),
    ]
    for issue_date, pattern_number, quantity, label in monthly_inventory_issues:
        issue_spare = Spares.objects.filter(pattern_number=pattern_number).first()
        if not issue_spare:
            continue
        issue_spare.quantity_authorised = max(
            issue_spare.quantity_authorised,
            issue_spare.quantity_available + quantity + 30,
        )
        issue_spare.quantity_available = max(
            issue_spare.quantity_available, quantity + 20
        )
        issue_spare.save(update_fields=["quantity_authorised", "quantity_available"])
        dart_number = f"INV-TREND-{issue_date:%Y%m}-{label}"
        existing_issue = Issue.objects.filter(dart_number=dart_number).first()
        if existing_issue:
            existing_issue.quantity_issued = quantity
            existing_issue.date_of_issue = issue_date
            existing_issue.save(update_fields=["quantity_issued", "date_of_issue"])
            continue
        Issue.objects.create(
            spare=issue_spare,
            equipment=equipment_name,
            date_of_issue=issue_date,
            username=getattr(
                users["Storekeeper"], "user_profile", users["Storekeeper"]
            ),
            quantity_issued=quantity,
            remarks="Ship inventory dashboard monthly trend seed",
            dart_number=dart_number,
        )

    refit_category = MRefitCategory.objects.get(refit_category_id=1)
    refit = MRefit.objects.get(refit_id=1)

    refit_periods_data = [
        ("AMP1-2026", "OPERATIONAL", "AMP", date(2026, 3, 16), date(2026, 3, 31)),
        ("EAMP1-2026", "REFIT", "EAMP", date(2026, 4, 16), date(2026, 4, 30)),
        ("EAMP-1-2025", "REFIT", "EAMP", date(2025, 4, 16), date(2025, 4, 30)),
        ("SMP-2-2026", "REFIT", "SMP", date(2026, 5, 1), date(2026, 5, 15)),
        ("MR-1-2025", "REFIT", "MR", date(2025, 6, 1), date(2025, 6, 30)),
    ]

    refit_period = None
    for name, maint_period, occasion, start_dt, end_dt in refit_periods_data:
        rp = upsert(
            RefitMaintenancePeriod,
            {"name": name},
            {
                "maintenance_period": maint_period,
                "occasion": occasion,
                "actual_start_date": start_dt,
                "actual_end_date": end_dt,
                "plan_start_date": start_dt,
                "plan_end_date": end_dt,
                "ship_universal_f_key": ships[0],
                "refit_category_f_key": refit_category,
                "universal_m_refit": refit,
            },
        )
        if refit_period is None:
            refit_period = rp

    # Seed MaintenanceOccasionMaster
    admin_user = users.get("1234")
    admin_profile = (
        getattr(admin_user, "user_profile", admin_user) if admin_user else None
    )
    m_occasions_seed = {
        "Operational": [
            "Normal RA",
            "Signal RA",
            "OPDEF",
            "Guarantee Defect",
            "AMP",
            "SMP",
            "EAMP",
            "Trial Unit Observations",
            "OST/ Workup Observations",
        ],
        "Refit": ["DL II", "SDL", "AWRF", "REFIT RA"],
    }
    for m_per, m_occs in m_occasions_seed.items():
        for m_occ in m_occs:
            upsert(
                MaintenanceOccasionMaster,
                {"maintenance_period": m_per, "occasion": m_occ},
                {"created_by": admin_user},
            )

    upsert(
        OpsMaintenancePeriod,
        {"name": f"{ships[0].name} Operational Window"},
        {
            "maintenance_period": "Harbour maintenance",
            "occasion": "Pre-sailing checks",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=5),
        },
    )
    if (
        table_exists(Delinquency)
        and table_exists(RefCompDelinquencyDetail)
        and table_exists(ABER)
    ):
        admin_p = getattr(users["1234"], "user_profile", users["1234"])
        dyhod_p = getattr(users["DyHOD"], "user_profile", users["DyHOD"])
        delinquency = upsert(
            Delinquency,
            {"delinquency_code": "A1"},
            {
                "delinquency_description": "Spares awaited",
                "active": True,
                "created_by": admin_p,
                "updated_by": admin_p,
            },
        )
        upsert(
            RefCompDelinquencyDetail,
            {"remarks": "Awaiting lube oil filter delivery"},
            {
                "ref_comp_id": refit_period,
                "ship_sr_no": 1,
                "refit_type": "SR",
                "refit_serial": 1,
                "equipment_ship_id": ship_equipment.id,
                "equipment_code": 1001,
                "loc_code": 120,
                "delinquency": delinquency,
                "delinquency_reason": "S",
                "authority": "HOD ME",
                "active": True,
                "created_by": users["1234"].id,
                "created_date": timezone.now(),
                "updated_by": users["DyHOD"].id,
                "updated_date": timezone.now(),
            },
        )
        upsert(
            ABER,
            {"reference_no": "ABER-SEED-001"},
            {
                "ship_id": ships[0],
                "equipment_id": master_equipment,
                "s_no": 1,
                "replace_equip_asbly": "Lube oil filter assembly",
                "avail_status": "Available",
                "aber_category": "Operational",
                "date_initiated": date.today() - timedelta(days=10),
                "plan_replace_date": date.today() + timedelta(days=20),
                "time_req_in_weeks": 3,
                "department_id": ctx["departments"]["ME"],
                "quantity": 1,
                "proposed_quantity": 1,
                "created_by": admin_p,
                "updated_by": dyhod_p,
                "active": True,
                "equipment_details": "Main gas turbine lube oil filtration assembly",
                "oem_details": "Bharat Defence Engineering",
            },
        )
    else:
        print("Skipped refit demo rows because refit database tables do not exist.")

    return {
        "sub_department": sub_department,
        "ship_equipment": ship_equipment,
        "master_equipment": master_equipment,
        "equipment_name": equipment_name,
    }


def seed_crew_manage(ctx, users):
    if not (ActionStationMaster and table_exists(ActionStationMaster)):
        print("Skipped crew_manage seed rows because crew_manage tables do not exist.")
        return

    now = timezone.now()
    admin_user = users["1234"]
    dyhod_user = users["DyHOD"]
    maintainer_user = users["Maintainer"]
    storekeeper_user = users["Storekeeper"]
    admin_profile = getattr(admin_user, "user_profile", admin_user)
    dyhod_profile = getattr(dyhod_user, "user_profile", dyhod_user)
    maintainer_profile = getattr(maintainer_user, "user_profile", maintainer_user)
    storekeeper_profile = getattr(storekeeper_user, "user_profile", storekeeper_user)

    for name in [
        "Damage Control HQ",
        "Bridge",
        "Fire Fighting Party No.1",
        "Machinery Control Room",
        "Flight Deck Party",
    ]:
        upsert(ActionStationMaster, {"name": name}, {})
    for name in [
        "Gun Direction Position",
        "Missile Control Room",
        "Anti-Submarine Control",
        "Electronic Warfare Room",
    ]:
        upsert(DefenceStationMaster, {"name": name}, {})
    for name in [
        "Bridge Watch",
        "Engine Room Watch",
        "Sonar Watch",
        "Radar Watch",
    ]:
        upsert(CruisingStationMaster, {"name": name}, {})
    for name in [
        "Forward Shelter",
        "Aft Shelter",
        "Machinery Space Shelter",
    ]:
        upsert(ShelterStationMaster, {"name": name}, {})
    for name in [
        "Emergency Steering Position",
        "Emergency Generator Room",
        "Casualty Clearing Station",
    ]:
        upsert(EmergencyStationMaster, {"name": name}, {})

    for rank_name, classification in [
        ("Captain", "Senior"),
        ("Commander", "Senior"),
        ("Lieutenant Commander", "Senior"),
        ("Lieutenant", "Senior"),
        ("Chief Petty Officer", "Senior"),
        ("Petty Officer", "Junior"),
    ]:
        upsert(
            SailorRankClassification,
            {"rank_name": rank_name},
            {"classification": classification},
        )

    for name in ["Temporary Duty - Course", "Temporary Duty - Attachment"]:
        upsert(TypeOfTempDuty, {"name": name}, {})
    for name in ["Air", "Rail", "Road", "Sea"]:
        upsert(ModeOfTravel, {"name": name}, {})
    for name in ["Field Service Ration", "Peace Ration", "Hard Ration"]:
        upsert(RationType, {"name": name}, {})
    for name in ["Rail Warrant", "Air Warrant", "Road Mileage"]:
        upsert(PassageType, {"name": name}, {})
    for name in ["Naval Dockyard Mumbai", "INS Shivaji", "Naval War College"]:
        upsert(PlaceOfTyDuty, {"name": name}, {})
    for name, leave_numbers in [
        ("Annual Leave", 60),
        ("Casual Leave", 10),
        ("Sick Leave", 30),
    ]:
        upsert(TypeOfLeave, {"name": name}, {"leave_numbers": leave_numbers})
    for name in ["Mumbai Central", "Visakhapatnam", "New Delhi"]:
        upsert(Railway, {"name": name}, {})
    for name in ["S1A1", "S2A2", "S3A3"]:
        upsert(MedicalCategory, {"name": name}, {})
    for name in ["8 Days", "10 Days"]:
        upsert(LtcDays, {"name": name}, {})

    address = None
    if AddressDetails and table_exists(AddressDetails):
        address = upsert(
            AddressDetails,
            {"email_permanent": "maintainer.home@navy.local"},
            {
                "address_permanent": "Naval Officers Colony, Mumbai",
                "country_permanent": "India",
                "number_permanent": "+91 90000 40001",
                "line1_other": "Naval Dockyard Quarters",
                "district_other": "Mumbai Suburban",
                "city_other": "Mumbai",
                "state_other": "Maharashtra",
                "country_other": "India",
                "pincode_other": "400001",
            },
        )

    leave_application_1 = upsert(
        LeaveApplication,
        {
            "personal_number": maintainer_profile.personal_number,
            "start_date": date.today() - timedelta(days=20),
        },
        {
            "rank": "Chief Petty Officer",
            "name": "Rohan Kapoor",
            "department": "Marine Engineering",
            "designation": "Maintainer",
            "leave_type": "On Leave",
            "end_date": date.today() - timedelta(days=10),
            "reporting_date": date.today() - timedelta(days=9),
            "station": "Mumbai",
            "reason": "Annual leave for family commitments.",
            "application_status": "Approved",
            "applied_by": maintainer_profile,
            "approved_rejected_by": dyhod_profile,
            "approved_rejected_at": now - timedelta(days=19),
        },
    )
    leave_application_2 = upsert(
        LeaveApplication,
        {
            "personal_number": storekeeper_profile.personal_number,
            "start_date": date.today() + timedelta(days=3),
        },
        {
            "rank": "Petty Officer",
            "name": "Karan Nair",
            "department": "Logistics",
            "designation": "Storekeeper",
            "leave_type": "Ty Duty",
            "end_date": date.today() + timedelta(days=6),
            "reporting_date": date.today() + timedelta(days=7),
            "station": "Naval Dockyard Mumbai",
            "reason": "Temporary duty for stores audit course.",
            "application_status": "Pending",
            "applied_by": storekeeper_profile,
        },
    )

    if PersonnelStatusLog and table_exists(PersonnelStatusLog):
        upsert(
            PersonnelStatusLog,
            {
                "personnel_number": maintainer_profile.personal_number,
                "log_date": date.today() - timedelta(days=15),
            },
            {
                "rank": "Chief Petty Officer",
                "name": "Rohan Kapoor",
                "department": "Marine Engineering",
                "designation": "Maintainer",
                "status": "On Leave",
                "leave_application": leave_application_1,
            },
        )
        upsert(
            PersonnelStatusLog,
            {
                "personnel_number": storekeeper_profile.personal_number,
                "log_date": date.today(),
            },
            {
                "rank": "Petty Officer",
                "name": "Karan Nair",
                "department": "Logistics",
                "designation": "Storekeeper",
                "status": "Present",
                "leave_application": leave_application_2,
            },
        )

    if LeaveDetails and table_exists(LeaveDetails):
        leave_detail = upsert(
            LeaveDetails,
            {
                "user_id": maintainer_profile.id,
                "start_date": date.today() - timedelta(days=20),
            },
            {
                "type_of_leave": "Annual Leave",
                "category_of_leave": "Annual",
                "commencement_date": date.today() - timedelta(days=20),
                "end_date": date.today() - timedelta(days=10),
                "no_of_days": 10,
                "leave_year": str(date.today().year),
                "leave_station": "Mumbai",
                "station_type": "Out",
                "railway_station": "Mumbai Central",
                "medical_category": "S1A1",
                "with_without_passage": "With Passage",
                "passage_type": "Rail Warrant",
                "ration_type": "Peace Ration",
                "remarks": "Seeded legacy leave record.",
                "address_id": address,
                "status": "Approved",
            },
        )

        if LeaveApprovalWorkflow and table_exists(LeaveApprovalWorkflow):
            upsert(
                LeaveApprovalWorkflow,
                {"leave_id": leave_detail},
                {
                    "dhod": str(dyhod_profile.id),
                    "dhod_action": "Approved",
                    "hod": str(dyhod_profile.id),
                    "hod_action": "Approved",
                    "co": str(admin_profile.id),
                    "co_action": "Approved",
                    "remarks": "Approved through seeded workflow.",
                },
            )

        if LeaveApprovalHistory and table_exists(LeaveApprovalHistory):
            upsert(
                LeaveApprovalHistory,
                {
                    "leave_id": leave_detail,
                    "approved_by_id": maintainer_profile.id,
                    "action_taken": "Pending",
                },
                {"ip_address": SYSTEM_IP},
            )
            upsert(
                LeaveApprovalHistory,
                {
                    "leave_id": leave_detail,
                    "approved_by_id": dyhod_profile.id,
                    "action_taken": "Approved",
                },
                {"ip_address": SYSTEM_IP},
            )

    if TemporaryDuty and table_exists(TemporaryDuty):
        temp_duty = upsert(
            TemporaryDuty,
            {
                "user_id": storekeeper_profile.id,
                "start_date": date.today() + timedelta(days=3),
            },
            {
                "temp_duty_type": "Temporary Duty - Course",
                "commencement_date": date.today() + timedelta(days=3),
                "end_date": date.today() + timedelta(days=6),
                "no_of_days": 3,
                "station_type": "Out",
                "gx_unit": "Naval Dockyard Mumbai",
                "place_of_duty": "Naval Dockyard Mumbai",
                "with_without_passage": "With Passage",
                "passage_type": "Rail Warrant",
                "ration_type": "Peace Ration",
                "authority_number": "NHQ/LOG/TD/2026/01",
                "authority_date": date.today() - timedelta(days=2),
                "remarks": "Seeded stores audit course attachment.",
                "address_id": address,
                "status": "Pending",
            },
        )

        if TemporaryDutyApprovalWorkflow and table_exists(
            TemporaryDutyApprovalWorkflow
        ):
            upsert(
                TemporaryDutyApprovalWorkflow,
                {"duty": temp_duty},
                {
                    "dhod": str(dyhod_profile.id),
                    "dhod_action": "Pending",
                    "remarks": "Awaiting HOD action.",
                },
            )

        if TemporaryDutyApprovalHistory and table_exists(TemporaryDutyApprovalHistory):
            upsert(
                TemporaryDutyApprovalHistory,
                {
                    "duty": temp_duty,
                    "user_id": storekeeper_profile.id,
                    "action": "Pending",
                },
                {
                    "user_name": "Karan Nair",
                    "level": "USER",
                    "remarks": "Application submitted.",
                },
            )

        if GXForm and table_exists(GXForm):
            upsert(
                GXForm,
                {"gx_no": "GX-2026-001"},
                {
                    "gx_date": now - timedelta(days=2),
                    "occurrence": "AM",
                    "leave_id": str(leave_application_2.id),
                },
            )

    civilian = None
    if CivilianOfficial and table_exists(CivilianOfficial):
        civilian = upsert(
            CivilianOfficial,
            {"ref_id": "CIV-0001"},
            {
                "name_snapshot": "Ramesh Iyer",
                "role": "Barber",
                "contact": "+91 90000 50001",
                "remarks": "Empanelled ship's barber.",
                "is_active": True,
                "person_type": "Civilian",
                "dept_snapshot": "Logistics",
                "created_by": admin_user,
            },
        )

    if Sailing and table_exists(Sailing):
        sailing = upsert(
            Sailing,
            {"name": "Fleet Exercise Alpha"},
            {
                "area": "Western Naval Command Exercise Area",
                "start_date": now - timedelta(days=5),
                "co_name": "Capt System Administrator",
                "xo_name": "Cdr Arjun Mehra",
                "remarks": "Seeded fleet sailing exercise.",
                "status": "active",
                "created_by": admin_user,
            },
        )
        if civilian:
            sailing.civilians.set([civilian])

        if SailingPersonnel and table_exists(SailingPersonnel):
            upsert(
                SailingPersonnel,
                {
                    "sailing": sailing,
                    "pno_snapshot": maintainer_profile.personal_number,
                },
                {
                    "profile": maintainer_profile,
                    "rank_snapshot": "Chief Petty Officer",
                    "name_snapshot": "Rohan Kapoor",
                    "dept_snapshot": "Marine Engineering",
                    "desig_snapshot": "Maintainer",
                    "person_type": "Naval",
                    "watch_station": "Machinery Control Room",
                    "action_station": "Machinery Control Room",
                    "status_override": "Present",
                    "created_by": admin_user,
                },
            )
            upsert(
                SailingPersonnel,
                {
                    "sailing": sailing,
                    "pno_snapshot": storekeeper_profile.personal_number,
                },
                {
                    "profile": storekeeper_profile,
                    "rank_snapshot": "Petty Officer",
                    "name_snapshot": "Karan Nair",
                    "dept_snapshot": "Logistics",
                    "desig_snapshot": "Storekeeper",
                    "person_type": "Naval",
                    "watch_station": "Stores Room",
                    "action_station": "Damage Control HQ",
                    "status_override": "Ty Duty",
                    "created_by": admin_user,
                },
            )

        if PersonnelAssignment and table_exists(PersonnelAssignment):
            upsert(
                PersonnelAssignment,
                {"sailing": sailing, "pno": maintainer_profile.personal_number},
                {
                    "name_snapshot": "Rohan Kapoor",
                    "rank_snapshot": "Chief Petty Officer",
                    "dept_snapshot": "Marine Engineering",
                    "action": "Machinery Control Room",
                    "defence": "Anti-Submarine Control",
                    "cruising": "Engine Room Watch",
                    "shelter": "Machinery Space Shelter",
                    "emergency": "Emergency Generator Room",
                    "mess": "Senior Rates Mess",
                    "section": "ME-MP",
                    "blood_group": "O+",
                },
            )
            upsert(
                PersonnelAssignment,
                {"sailing": sailing, "pno": storekeeper_profile.personal_number},
                {
                    "name_snapshot": "Karan Nair",
                    "rank_snapshot": "Petty Officer",
                    "dept_snapshot": "Logistics",
                    "action": "Damage Control HQ",
                    "defence": "Missile Control Room",
                    "cruising": "Bridge Watch",
                    "shelter": "Forward Shelter",
                    "emergency": "Casualty Clearing Station",
                    "mess": "Junior Rates Mess",
                    "section": "LOG-STORES",
                    "blood_group": "B+",
                },
            )


def seed_hotwork(ctx, users, refs):
    if not (AddHotwork and table_exists(AddHotwork)):
        print("Skipped hotwork seed rows because hotwork tables do not exist.")
        return

    now = timezone.now()
    admin_profile = getattr(users["1234"], "user_profile", users["1234"])
    dyhod_profile = getattr(users["DyHOD"], "user_profile", users["DyHOD"])
    maintainer_profile = getattr(
        users["Maintainer"], "user_profile", users["Maintainer"]
    )
    sub_department = refs.get("sub_department")

    hotwork_rows = [
        {
            "hotwork_code": "HW-2026-001",
            "date_of_hotwork": date.today() - timedelta(days=10),
            "location_of_hotwork": "Main Machinery Room, Frame 120",
            "type_of_hotwork": "WELDING",
            "approval_status": "approved",
            "is_completed": True,
        },
        {
            "hotwork_code": "HW-2026-002",
            "date_of_hotwork": date.today() + timedelta(days=2),
            "location_of_hotwork": "Fire Pump Room, Frame 85",
            "type_of_hotwork": "CUTTING_WELDING",
            "approval_status": "pending_hods",
            "is_completed": False,
        },
    ]

    hotworks = []
    for row in hotwork_rows:
        completed = row["is_completed"]
        hotwork = upsert(
            AddHotwork,
            {"hotwork_code": row["hotwork_code"]},
            {
                "holiday_or_working_day": "WORKING_DAY",
                "date_of_hotwork": row["date_of_hotwork"],
                "sub_department": sub_department,
                "sentries_required": True,
                "location_of_hotwork": row["location_of_hotwork"],
                "type_of_hotwork": row["type_of_hotwork"],
                "departmental_officer": "Lt Cdr Vikram Rao",
                "all_adjacent_compartments": "MMR-2, Fuel Tank Space",
                "sentry_names": "AB Karan Nair, Ldg Smn Rohan Kapoor",
                "hotwork_incharge": maintainer_profile,
                "dl_number": f"DL/{row['hotwork_code']}",
                "supervision_welder_name": "Welder Suresh",
                "manager_of_concern_center": "PO Karan Nair",
                "officer_of_the_day": admin_profile,
                "remarks": "Seeded hotwork demo record.",
                "night_work": False,
                "created_by": admin_profile,
                "approval_status": row["approval_status"],
                "incharge_approved": True,
                "incharge_approved_by": maintainer_profile,
                "incharge_approved_at": now,
                "dyhod_approved": completed,
                "dyhod_approved_by": dyhod_profile if completed else None,
                "dyhod_approved_at": now if completed else None,
                "all_hods_approved": completed,
                "ood_approved": completed,
                "ood_approved_by": admin_profile if completed else None,
                "ood_approved_at": now if completed else None,
                "is_started": True,
                "started_by": maintainer_profile,
                "started_at": now - timedelta(hours=2),
                "is_completed": completed,
                "completed_by": maintainer_profile if completed else None,
                "completed_at": now if completed else None,
                "completion_remarks": "Hotwork closed, area inspected."
                if completed
                else None,
            },
        )
        hotworks.append(hotwork)

    if HotworkHODApproval and table_exists(HotworkHODApproval):
        for dept_code in ("ME", "EE", "WE"):
            upsert(
                HotworkHODApproval,
                {"hotwork": hotworks[0], "department": ctx["departments"][dept_code]},
                {
                    "approved": True,
                    "approved_by": dyhod_profile,
                    "approved_at": now,
                    "earthing_gts": "Yes",
                    "fire_sensor_ops": "OPS",
                    "flood_sensor_ops": "OPS",
                    "supply_point": "YES",
                    "iccp_off": "YES",
                    "fire_extinguisher": "YES",
                    "fire_hose": "YES",
                    "firemain_pressure": "YES",
                    "free_lagging": "YES",
                    "sentry_knowledge": "YES",
                },
            )
        upsert(
            HotworkHODApproval,
            {"hotwork": hotworks[1], "department": ctx["departments"]["ME"]},
            {
                "approved": True,
                "approved_by": dyhod_profile,
                "approved_at": now,
                "earthing_gts": "Yes",
                "fire_extinguisher": "YES",
                "fire_hose": "YES",
                "sentry_knowledge": "YES",
            },
        )

    if HotworkProgressActivity and table_exists(HotworkProgressActivity):
        upsert(
            HotworkProgressActivity,
            {"hotwork": hotworks[0], "action": "started"},
            {"performed_by": maintainer_profile, "remarks": "Hotwork commenced."},
        )
        upsert(
            HotworkProgressActivity,
            {"hotwork": hotworks[0], "action": "completed"},
            {"performed_by": maintainer_profile, "remarks": "Hotwork closed out."},
        )
        upsert(
            HotworkProgressActivity,
            {"hotwork": hotworks[1], "action": "started"},
            {"performed_by": maintainer_profile, "remarks": "Awaiting HOD sign-off."},
        )


def seed_inout_tag(ctx, users, refs):
    if not (TagOut and table_exists(TagOut)):
        print("Skipped inout_tag seed rows because inout_tag tables do not exist.")
        return

    now = timezone.now()
    admin_profile = getattr(users["1234"], "user_profile", users["1234"])
    dyhod_profile = getattr(users["DyHOD"], "user_profile", users["DyHOD"])
    maintainer_profile = getattr(
        users["Maintainer"], "user_profile", users["Maintainer"]
    )
    ship_equipment = refs.get("ship_equipment")

    tagout_open = upsert(
        TagOut,
        {"name_of_component": "Main Gas Turbine Lube Oil Pump", "type": "danger"},
        {
            "date": date.today() - timedelta(days=5),
            "user_profile": maintainer_profile,
            "tagout_equipment_name": ship_equipment,
            "name_of_subsystem": "Lube Oil System",
            "serial_number_of_component": "GT-LOP-SN-001",
            "pattern_number_of_component": "GT-LOP-001",
            "weight_of_component": Decimal("45.50"),
            "condition": "non_ops",
            "special_instructions": "Isolate lube oil supply before removal.",
            "tagout_reason": "repair_or_overhauling",
            "tagout_description": "Removed for overhaul of worn bearing.",
            "tagout_maintainer_name_rank": "PO Karan Nair",
            "repair_ra_number": "RA-SEED-001",
            "repair_landed_details": "Landed to Naval Dockyard workshop.",
            "repair_item_taken_by": "Naval Dockyard Team",
            "expected_date_of_tagin": date.today() + timedelta(days=10),
            "approval_status": "approved",
            "approved_by": dyhod_profile,
            "approved_on": now,
            **base_defaults(admin_profile),
        },
    )
    tagout_open.departments_affected.set(
        [ctx["departments"]["ME"], ctx["departments"]["EE"]]
    )

    tagout_closed = upsert(
        TagOut,
        {"name_of_component": "Fire Pump Motor", "type": "warning"},
        {
            "date": date.today() - timedelta(days=25),
            "user_profile": maintainer_profile,
            "tagout_equipment_name": ship_equipment,
            "name_of_subsystem": "Fire Fighting System",
            "serial_number_of_component": "FP-MOT-SN-002",
            "pattern_number_of_component": "FP-MOT-002",
            "weight_of_component": Decimal("60.00"),
            "condition": "non_ops",
            "special_instructions": "Ensure standby fire pump is operational.",
            "tagout_reason": "survey_and_demand",
            "tagout_description": "Landed for survey ahead of demand.",
            "tagout_maintainer_name_rank": "CPO Rohan Kapoor",
            "survery_demand_authority": "NHQ/ME/SURVEY/2026",
            "expected_date_of_tagin": date.today() - timedelta(days=5),
            "approval_status": "approved",
            "approved_by": dyhod_profile,
            "approved_on": now - timedelta(days=20),
            **base_defaults(admin_profile),
        },
    )
    tagout_closed.departments_affected.set([ctx["departments"]["ME"]])

    if TagIn and table_exists(TagIn):
        tagin_closed = upsert(
            TagIn,
            {"tagout": tagout_closed},
            {
                "tagin_date": date.today() - timedelta(days=5),
                "tagin_description": "Fire pump motor reinstalled after survey.",
                "tagin_maintainer": "CPO Rohan Kapoor",
                "all_items_returned": True,
                "status": "completed",
                "approval_status": "approved",
                "tagin_remarks": "Motor tested satisfactorily.",
                "tagin_maintainer_name_rank": "CPO Rohan Kapoor",
                **base_defaults(admin_profile),
            },
        )

        if TagInApproval and table_exists(TagInApproval):
            upsert(
                TagInApproval,
                {"tagin": tagin_closed, "department": ctx["departments"]["ME"]},
                {
                    "approval_status": "approved",
                    "approved_by": dyhod_profile,
                    "approved_on": now - timedelta(days=4),
                    "remarks": "Reinstallation verified.",
                    **base_defaults(admin_profile),
                },
            )


def seed_messages(users):
    if not UserMessage or not table_exists(UserMessage):
        print(
            "Skipped seeding messages because UserMessage model or table does not exist."
        )
        return
    UserMessage.objects.update_or_create(
        sender=users["1234"],
        recipient=users["1234"],
        msg_title="Weekly Readiness Review",
        defaults={
            "msg_short_title": "Readiness review",
            "msg_body": "Submit department equipment status before the Friday readiness review.",
            "status": "unread",
        },
    )
    UserMessage.objects.update_or_create(
        sender=users["1234"],
        recipient=users["Maintainer"],
        msg_title="Main Gas Turbine Routine",
        defaults={
            "msg_short_title": "GT routine",
            "msg_body": "Complete monthly GT lube oil checks and update RH readings.",
            "status": "high_priority",
        },
    )


def next_index(model):
    return model.objects.count() + 1


def text_value(model, field, index):
    name = field.name.lower()
    model_name = model.__name__
    word = NAVY_WORDS[(index - 1) % len(NAVY_WORDS)]
    equipment = EQUIPMENT_WORDS[(index - 1) % len(EQUIPMENT_WORDS)]

    if name == "username":
        return f"seed_user_{index:03d}"
    if name == "password":
        return make_password(SEED_PASS)
    if "email" in name or "mail" in name:
        return f"{model_name.lower()}{index:03d}@navy.local"
    if "phone" in name or "contact" in name or "mobile" in name:
        return f"+91 90000 {index % 100000:05d}"
    if "ship" in name and "name" in name:
        return f"INS {word}"
    if name in {"name", "title", "role_title", "filename"} or name.endswith("_name"):
        if "equipment" in model_name.lower() or "equipment" in name:
            return f"{equipment} {index:03d}"
        if "ship" in model_name.lower():
            return f"INS {word} {index:03d}"
        return f"{model_name} {word} {index:03d}"
    if "first_name" in name:
        return ["Arjun", "Vikram", "Neha", "Rohan", "Karan"][index % 5]
    if "last_name" in name:
        return ["Mehra", "Rao", "Singh", "Kapoor", "Nair"][index % 5]
    if "rank" in name:
        return ["Captain", "Commander", "Lieutenant Commander", "Chief Petty Officer"][
            index % 4
        ]
    if "designation" in name:
        return ["CO", "Dy HOD", "Maintainer", "Storekeeper", "Admin Officer"][index % 5]
    if "code" in name or name.endswith("_no") or "number" in name or "serial" in name:
        prefix = "".join(ch for ch in model_name.upper() if ch.isalpha())[:6] or "SWMM"
        return f"{prefix}-{index:04d}"
    if "status" in name:
        return "ACTIVE"
    if "category" in name:
        return "Operational"
    if "authority" in name:
        return "Naval Headquarters"
    if "location" in name:
        return "Main Machinery Compartment"
    if "compartment" in name:
        return f"MMR-{(index % 4) + 1}"
    if (
        "remarks" in name
        or "description" in name
        or "detail" in name
        or field.get_internal_type() == "TextField"
    ):
        return f"Seeded Navy realistic entry {index} for {model_name}: {equipment} readiness and maintenance data."


def value_for_field(model, field, index):
    if getattr(field, "choices", None):
        choices = [choice[0] for choice in field.choices if choice[0] not in ("", None)]
        if choices:
            return choices[(index - 1) % len(choices)]

    field_type = field.get_internal_type()
    if field_type == "SlugField":
        return f"{model.__name__.lower()}-{field.name.lower()}-{index:04d}"[
            : getattr(field, "max_length", 50)
        ]
    if field_type in {"CharField", "TextField", "EmailField"}:
        value = text_value(model, field, index)
        max_length = getattr(field, "max_length", None)
        if max_length:
            value = value[:max_length]
        return value
    if field_type in {
        "IntegerField",
        "PositiveIntegerField",
        "SmallIntegerField",
        "PositiveSmallIntegerField",
        "BigIntegerField",
        "PositiveBigIntegerField",
    }:
        if "active" in field.name.lower():
            return 1
        if "status" in field.name.lower():
            return 1
        return index
    if field_type == "BooleanField":
        return True
    if field_type == "DecimalField":
        return Decimal(f"{index}.00")
    if field_type == "FloatField":
        return float(index)
    if field_type == "DateField":
        return date.today() + timedelta(days=index)
    if field_type == "DateTimeField":
        return timezone.now() + timedelta(days=index)
    if field_type == "TimeField":
        return time(8 + (index % 8), 30)
    if field_type in {"FileField", "ImageField"}:
        value = image_ref(
            PROFILE_IMAGE if "user" in model.__name__.lower() else SHIP_IMAGE
        )
        max_length = getattr(field, "max_length", None)
        if max_length and len(value) > max_length:
            value = value[-max_length:]
        return value
    if field_type == "GenericIPAddressField":
        return SYSTEM_IP
    if field_type == "DurationField":
        return timedelta(hours=index)
    if field_type == "JSONField":
        return {"source": "seed", "index": index}
    return None


def create_generic_instance(model, index):
    if model is User:
        ship = Ship.objects.order_by("id").first()
        department = Department.objects.order_by("id").first()
        pn = f"PN{1000 + index}"
        profile = None
        if CustomUserProfile:
            profile, _ = CustomUserProfile.objects.update_or_create(
                personal_number=pn,
                defaults={
                    "firstname": f"SeedUser{index:03d}",
                    "lastname": "Seeded",
                    "designation": "Watchkeeper",
                    "department": department,
                    "ship": ship,
                    "has_credentials": True,
                    "user_active": True,
                    "date_of_birth": date(1990, 1, min((index % 28) + 1, 28)),
                },
            )
        user_defaults = {
            "password": make_password(SEED_PASS),
            "is_active": True,
            "is_admin": False,
        }
        if profile:
            user_defaults["user_profile"] = profile

        return User.objects.create(
            username=f"seed_user_{index:03d}",
            **user_defaults,
        )

    if model._meta.app_label == "obs" and model.__name__ == "Spares":
        equipment_class = EquipmentClass.objects.order_by("?").first()
        denomination = Denomination.objects.order_by("?").first()
        authority = Authority.objects.order_by("?").first()
        if not equipment_class or not authority:
            return None
        return model.objects.create(
            equipment_class=equipment_class,
            pattern_number=f"spare-{index:04d}",
            description=f"LUBE OIL FILTER ELEMENT {index:03d}",
            category=model.CONSUMABLE,
            critical=index % 2 == 0,
            compartment=f"MMR-{(index % 4) + 1}",
            location="STORE ROOM",
            rack_position=f"A{index}",
            rack_number=f"R{index}",
            denomination=denomination,
            quantity_authorised=30,
            quantity_available=30,
            authority=authority,
            page=f"page-{index:04d}",
            line=str(index),
            remarks="CRITICAL PROPULSION SPARE",
            image=image_ref(SHIP_IMAGE),
        )

    if model._meta.app_label == "obs" and model.__name__ == "Issue":
        spare = Spares.objects.filter(quantity_available__gte=1).order_by("?").first()
        user = User.objects.order_by("?").first()
        equipment = EquipmentName.objects.order_by("?").first()
        if not spare or not user:
            return None
        return model.objects.create(
            spare=spare,
            equipment=equipment,
            username=getattr(user, "user_profile", user),
            quantity_issued=1,
            remarks="ISSUED FOR SEEDED ROUTINE",
            dart_number=f"DART-SEED-{index:04d}",
        )

    if model._meta.app_label == "obs" and model.__name__ == "Return":
        spare = Spares.objects.order_by("?").first()
        user = User.objects.order_by("?").first()
        command = MShipCommand.objects.order_by("?").first()
        ship = Ship.objects.order_by("?").first()
        if not spare:
            return None
        return model.objects.create(
            spare_id=spare,
            command_id=command,
            ship=ship,
            username=user.username if user else "SEED",
            returned_by=getattr(user, "user_profile", user),
            remarks="SEEDED RETURN ENTRY",
            quantity_returned=0,
        )

    if model._meta.app_label == "obs" and model.__name__ == "PostReceive":
        spare = Spares.objects.order_by("?").first()
        issue = Issue.objects.order_by("?").first()
        user = User.objects.order_by("?").first()
        if not spare:
            return None
        return model.objects.create(
            spare=spare,
            issue_entry=issue,
            quantity_received=0,
            receipt_number=f"receipt-{index:04d}",
            receive_date=timezone.now(),
            remarks="SEEDED RECEIPT ENTRY",
            dart_number=f"DART-SEED-{index:04d}",
            created_by=user.username if user else "SEED",
            created_by_user=user,
        )

    if model._meta.app_label == "obs" and model.__name__ == "PlannedRoutineSpareList":
        planned_model = apps.get_model("ems", "PlannedRoutineDescription")
        routine_description = RoutineDescription.objects.order_by("?").first()
        if not routine_description or not table_exists(planned_model):
            return None
        planned, _ = planned_model.objects.get_or_create(
            routine_description_id=routine_description,
            defaults={
                "spares_required": True,
                "planned_commencement_date": date.today() + timedelta(days=index),
                "is_deleted": False,
            },
        )
        return model.objects.create(
            planned_routine_description=planned,
            pattern_number=f"OBS-PLANNED-{index:04d}",
            quantity_required=(index % 5) + 1,
            is_deleted=False,
        )

    if model._meta.app_label == "work_manage" and model.__name__ == "TimeSlot":
        user = User.objects.order_by("id")[index % max(User.objects.count(), 1)]
        department = Department.objects.order_by("?").first()
        hour = 6 + (index % 10)
        return model.objects.create(
            user=user,
            created_by=user,
            department=department,
            date=date.today() + timedelta(days=index),
            from_time=time(hour, 0),
            to_time=time(hour + 1, 0),
            is_active=True,
        )

    if model._meta.app_label == "work_manage" and model.__name__ == "WorkAssignment":
        assigner = User.objects.order_by("id").first()
        assignee = User.objects.order_by("id")[index % max(User.objects.count(), 1)]
        timeslot = (
            __import__("work_manage.models", fromlist=["TimeSlot"])
            .TimeSlot.objects.order_by("?")
            .first()
        )
        duty = (
            __import__("work_manage.models", fromlist=["Duty"])
            .Duty.objects.order_by("?")
            .first()
        )
        department = Department.objects.order_by("?").first()
        if not assigner or not assignee or not timeslot or not duty:
            return None
        return model.objects.create(
            assigner=assigner,
            created_by=assigner,
            assignee=assignee,
            timeslot=timeslot,
            duty=duty,
            department=department,
            assignment_date=timeslot.date,
            notes=f"Seeded ship duty assignment {index}",
            role="Watchkeeper",
            location="at_harbour",
            status="ASSIGNED",
        )

    if (
        model._meta.app_label == "activity_planner"
        and model.__name__ == "PlannerActivity"
    ):
        user = User.objects.order_by("id").first()
        department = Department.objects.order_by("?").first()
        ship = Ship.objects.order_by("?").first()
        hour = (index % 10) + 6
        return model.objects.create(
            title=f"Planner Activity {index:03d}",
            date=date.today() + timedelta(days=index),
            start_time=time(hour, 0),
            end_time=time(hour + 2, 0),
            department=department,
            ship=ship,
            created_by=user,
            active=True,
        )

    data = {}
    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False) or field.many_to_many:
            continue
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            continue
        if field.primary_key and isinstance(
            field,
            (
                django_models.AutoField,
                django_models.BigAutoField,
                django_models.SmallAutoField,
            ),
        ):
            continue

        if field.is_relation and getattr(field, "related_model", None):
            related = field.related_model.objects.order_by("?").first()
            if related is None:
                if field.null or field.blank:
                    data[field.name] = None
                    continue
                return None
            data[field.name] = related
            continue

        value = value_for_field(model, field, index)
        if (
            value is None
            and not field.null
            and not field.blank
            and not field.has_default()
        ):
            return None
        if value is not None:
            data[field.name] = value

    obj = model.objects.create(**data)
    for field in model._meta.get_fields():
        if field.many_to_many and getattr(field, "related_model", None):
            related = list(field.related_model.objects.order_by("id")[:3])
            if related:
                getattr(obj, field.name).set(related)
    return obj


def fill_model_to_count(model, target_count):
    current = model.objects.count()
    if current >= target_count:
        return 0, None

    created = 0
    failures = []
    max_attempts = max((target_count - current) * 12, 24)
    for attempt in range(1, max_attempts + 1):
        if model.objects.count() >= target_count:
            break
        index = next_index(model) + attempt
        try:
            with transaction.atomic():
                obj = create_generic_instance(model, index)
            if obj is not None:
                created += 1
        except Exception as exc:
            failures.append(str(exc))

    if model.objects.count() < target_count:
        reason = failures[-1] if failures else "missing required dependency"
        return created, reason[:180]
    return created, None


def fill_all_project_tables(target_count):
    if target_count <= 0:
        return

    print(f"Top-up target: at least {target_count} rows per project table.")
    skipped = []
    for model in dependency_sorted_models(project_models()):
        if model._meta.auto_created:
            continue
        if model.__name__ in (
            "RefitMaintenancePeriod",
            "MaintenanceOccasionMaster",
            "ChMasterShipRemarksBy",
        ):
            continue
        created, reason = fill_model_to_count(model, target_count)
        if created:
            print(f"  {model._meta.app_label}.{model.__name__}: created {created}")
        if reason:
            skipped.append(f"{model._meta.app_label}.{model.__name__}: {reason}")

    if skipped:
        print("Tables not fully topped up:")
        for item in skipped:
            print(f"  {item}")


def inventory_models():
    inventory_app_labels = {"ilms", "obs", "wlms"}
    return [
        model
        for model in apps.get_models()
        if model._meta.app_label in inventory_app_labels and table_exists(model)
    ]


def seed_inventory_tables(target_count=10):
    print(
        "Inventory seed target: at least "
        f"{target_count} rows in every ILMS/WLMS/OBS table."
    )
    skipped = []
    for model in dependency_sorted_models(inventory_models()):
        if model._meta.auto_created:
            continue
        created, reason = fill_model_to_count(model, target_count)
        if created:
            print(f"  {model._meta.app_label}.{model.__name__}: created {created}")
        if reason:
            skipped.append(f"{model._meta.app_label}.{model.__name__}: {reason}")

    if skipped:
        print("Inventory tables not fully topped up:")
        for item in skipped:
            print(f"  {item}")


def seed_sfd_tables(target_count=10):
    if not SEED_SFD_DEMO_DATA:
        print("Skipped SFD demo table seed; CMMS sync verification mode is active.")
        return

    target_count = max(target_count, 10)
    print(f"SFD seed target: at least {target_count} rows in every SFD table.")
    call_command("populate_db", count=target_count)


def main():
    parser = argparse.ArgumentParser(
        description="Seed SWMM backend with Navy/ship demo data."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear seeded demo tables before inserting.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Top up every project table to at least this many rows.",
    )
    args = parser.parse_args()
    apply_legacy_dart_seed_column_compatibility()

    with transaction.atomic():
        if args.clear:
            clear_seeded_data()
        ctx = seed_masters()
        ships = seed_ships(ctx)
        users = seed_users(ctx, ships)
        seed_users_extra(ctx, users)
        seed_landing(users, ships)
        refs = seed_equipment_and_work(ctx, users, ships)
        seed_crew_manage(ctx, users)
        seed_hotwork(ctx, users, refs)
        seed_inout_tag(ctx, users, refs)
        seed_messages(users)
        seed_inventory_tables(10)
        seed_sfd_tables(args.count)
        fill_all_project_tables(args.count)

    print("Seed completed.")
    print(
        "Superuser usernames: 1234, shipadmin, co, DyHOD, Admin, Maintainer, Storekeeper"
    )
    print("Password for all seeded users: 12345")


if __name__ == "__main__":
    main()
