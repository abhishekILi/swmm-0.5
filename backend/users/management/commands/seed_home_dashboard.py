from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from activity_planner.models import PlannerActivity
from dart.models import CompleteDefectDart, CompletedRoutine, InitiateDart
from ems.models import (
    AddRoutineDetails,
    EquipmentName,
    MaintopHeader,
    RoutineDescription,
    SectionName,
    UniqueRoutineName,
)
from inout_tag.models import TagIn, TagOut
from master.models import Department, Ship, UnitType
from obs.models import Authority, Denomination, EquipmentClass, SpareClass, Spares
from sfd.models import ShipEquipment


class Command(BaseCommand):
    help = (
        "Create or update demo records required by the Home Dashboard API "
        "without touching seed files."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="home.dashboard.demo",
            help="User to assign dashboard-scoped records to. Default: home.dashboard.demo",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"].strip()
        today = timezone.localdate()
        now = timezone.now()

        departments = self._ensure_departments()
        ship = self._ensure_ship()
        user = self._ensure_user(username, departments["ENG"], ship)
        sections = self._ensure_sections(departments)
        equipment_names = self._ensure_equipment_names(sections)
        ship_equipment = self._ensure_ship_equipment(ship, departments, equipment_names)
        self._ensure_maintops(now)
        routine_descriptions = self._ensure_completed_routine_sources(equipment_names)
        self._ensure_completed_routines(routine_descriptions, today)
        defects = self._ensure_defects(departments["ENG"], equipment_names, today)
        self._ensure_completed_defects(defects, today)
        self._ensure_spares(departments["ENG"])
        self._ensure_planner_activities(departments, ship, user, today)
        self._ensure_tagout_workflow(
            user, ship_equipment["main_engine"], departments["ENG"], today
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Home dashboard demo data is ready: departments, hierarchy, maintops, "
                "defects, completed routines, spares, planner activities, and tag flows."
            )
        )

    def _ensure_departments(self):
        department_specs = [
            ("ENG", "Engineering"),
            ("ELE", "Electrical"),
            ("LOG", "Logistics"),
        ]
        departments = {}
        for code, name in department_specs:
            department, _ = Department.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "dep_code": code,
                    "description": f"{name} home dashboard demo department",
                },
            )
            updates = []
            if department.name != name:
                department.name = name
                updates.append("name")
            if department.dep_code != code:
                department.dep_code = code
                updates.append("dep_code")
            if updates:
                department.save(update_fields=updates)
            departments[code] = department
        return departments

    def _ensure_ship(self):
        unit_type, _ = UnitType.objects.get_or_create(
            name="Home Dashboard Demo Unit Type"
        )
        ship, _ = Ship.objects.get_or_create(
            code="HD-001",
            defaults={
                "name": "Home Dashboard Demo Ship",
                "sr_no": "HD-001",
                "ship_description": "Dashboard seed vessel",
                "ship_role_description": "Demo operational platform",
                "unit_type": unit_type,
                "unit_type_string": unit_type.name,
            },
        )
        updates = []
        if ship.name != "Home Dashboard Demo Ship":
            ship.name = "Home Dashboard Demo Ship"
            updates.append("name")
        if ship.sr_no != "HD-001":
            ship.sr_no = "HD-001"
            updates.append("sr_no")
        if ship.unit_type_id != unit_type.id:
            ship.unit_type = unit_type
            updates.append("unit_type")
        if ship.unit_type_string != unit_type.name:
            ship.unit_type_string = unit_type.name
            updates.append("unit_type_string")
        if updates:
            ship.save(update_fields=updates)
        return ship

    def _ensure_user(self, username, department, ship):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "personnel_number": "HD1001",
                "first_name": "Home",
                "last_name": "Dashboard",
                "rank": "Cdr",
                "unit": "Demo Unit",
                "designation": "Engineering Officer",
                "department": department,
                "ship": ship,
                "nud_mail": f"{username}@example.com",
            },
        )
        if created:
            user.set_password("Pass@12345")
            user.save(update_fields=["password"])

        updates = []
        if user.department_id != department.id:
            user.department = department
            updates.append("department")
        if user.ship_id != ship.id:
            user.ship = ship
            updates.append("ship")
        if not user.personnel_number:
            user.personnel_number = "HD1001"
            updates.append("personnel_number")
        if not user.nud_mail:
            user.nud_mail = f"{username}@example.com"
            updates.append("nud_mail")
        if updates:
            user.save(update_fields=updates)
        return user

    def _ensure_sections(self, departments):
        section_specs = [
            ("Machinery", departments["ENG"]),
            ("Hull Systems", departments["ENG"]),
            ("Power", departments["ELE"]),
            ("Supply", departments["LOG"]),
        ]
        sections = {}
        for name, department in section_specs:
            section, _ = SectionName.objects.get_or_create(
                name=name,
                department=department,
            )
            sections[name] = section
        return sections

    def _ensure_equipment_names(self, sections):
        equipment_specs = [
            ("Main Engine", sections["Machinery"], 1240.0, "ACTIVE"),
            ("Reduction Gear", sections["Machinery"], 830.0, "INACTIVE"),
            ("Steering Gear", sections["Hull Systems"], 410.0, "INACTIVE"),
            ("Ship Service Generator", sections["Power"], 920.0, "ACTIVE"),
            ("Cold Storage Compressor", sections["Supply"], 205.0, "INACTIVE"),
        ]
        equipment_names = {}
        for name, section, rhsi, state in equipment_specs:
            equipment, _ = EquipmentName.objects.get_or_create(
                name=name,
                section=section,
                defaults={
                    "nomenclature": name.upper(),
                    "rhsi": rhsi,
                    "state": state,
                    "started_at_location": "AT HARBOUR",
                    "equipment_code": name[:3].upper() + "-HD",
                },
            )
            updates = []
            if equipment.rhsi != rhsi:
                equipment.rhsi = rhsi
                updates.append("rhsi")
            if equipment.state != state:
                equipment.state = state
                updates.append("state")
            if equipment.started_at_location != "AT HARBOUR":
                equipment.started_at_location = "AT HARBOUR"
                updates.append("started_at_location")
            if updates:
                equipment.save(update_fields=updates)
            equipment_names[name] = equipment
        return equipment_names

    def _ensure_ship_equipment(self, ship, departments, equipment_names):
        equipment_specs = [
            ("HD-EQ-001", "Main Engine", departments["ENG"], "Machinery Space"),
            ("HD-EQ-002", "Reduction Gear", departments["ENG"], "Gear Room"),
            ("HD-EQ-003", "Steering Gear", departments["ENG"], "Steering Flat"),
            (
                "HD-EQ-004",
                "Ship Service Generator",
                departments["ELE"],
                "Generator Room",
            ),
            (
                "HD-EQ-005",
                "Cold Storage Compressor",
                departments["LOG"],
                "Provision Store",
            ),
        ]
        ship_equipment = {}
        for detail_code, name, department, location in equipment_specs:
            equipment, _ = ShipEquipment.objects.get_or_create(
                t_equipment_ship_detail=detail_code,
                defaults={
                    "ship": ship,
                    "department": department,
                    "nomenclature": name,
                    "equipment_name": name,
                    "equipment_code": detail_code,
                    "location_on_board": location,
                    "status": "active",
                },
            )
            updates = []
            if equipment.ship_id != ship.id:
                equipment.ship = ship
                updates.append("ship")
            if equipment.department_id != department.id:
                equipment.department = department
                updates.append("department")
            if equipment.nomenclature != name:
                equipment.nomenclature = name
                updates.append("nomenclature")
            if equipment.location_on_board != location:
                equipment.location_on_board = location
                updates.append("location_on_board")
            if updates:
                equipment.save(update_fields=updates)
            ship_equipment[name.lower().replace(" ", "_")] = equipment
        return ship_equipment

    def _ensure_maintops(self, now):
        maintop_specs = [
            (
                910001,
                "MT-HD-001",
                "Main Engine Lubrication Inspection",
                now - timedelta(days=25),
            ),
            (
                910002,
                "MT-HD-002",
                "Generator Cooling Water Check",
                now - timedelta(days=20),
            ),
            (
                910003,
                "MT-HD-003",
                "Steering Gear Functional Trial",
                now - timedelta(days=12),
            ),
            (
                910004,
                "MT-HD-004",
                "Cold Store Preservation Routine",
                now - timedelta(days=5),
            ),
        ]
        for maintop_id, maintop_no, title, created_date in maintop_specs:
            MaintopHeader.objects.update_or_create(
                maintop_id=maintop_id,
                defaults={
                    "maintop_no": maintop_no,
                    "maintop_title": title,
                    "department": "ENG",
                    "active": True,
                    "created_date": created_date,
                    "reference": "HOME-DASHBOARD-DEMO",
                },
            )

    def _ensure_completed_routine_sources(self, equipment_names):
        routine_name, _ = UniqueRoutineName.objects.get_or_create(
            name="HOME DASHBOARD ROUTINE"
        )
        routine_specs = [
            (
                "RD-HD-001",
                equipment_names["Main Engine"],
                "Inspect lube oil pump and strainers",
            ),
            (
                "RD-HD-002",
                equipment_names["Ship Service Generator"],
                "Calibrate protection relay settings",
            ),
        ]
        descriptions = {}
        for maintop_no, equipment, description in routine_specs:
            add_routine, _ = AddRoutineDetails.objects.get_or_create(
                maintop_no=maintop_no,
                equipment_name=equipment,
                routine_name=routine_name,
                defaults={
                    "routine_no": maintop_no,
                    "routine_category": "ALTERNATE PERIODIC",
                    "frequency": "6 MONTHS",
                    "frequency_in_months": 6,
                    "frequency_in_hours": 300,
                    "last_routine_completion_date": timezone.now() - timedelta(days=60),
                    "last_routine_completion_atrunning_hrs": 180.0,
                    "remarks": "HOME-DASHBOARD-DEMO",
                },
            )
            routine_description, _ = RoutineDescription.objects.get_or_create(
                add_routine_details=add_routine,
                routine_no=maintop_no,
                defaults={
                    "equipment_name": equipment,
                    "routine_name": routine_name,
                    "maintop_no": maintop_no,
                    "routine_description": description,
                    "by_whom": "DYD",
                    "due_date": timezone.localdate() + timedelta(days=15),
                    "previous_completed_date": timezone.localdate()
                    - timedelta(days=30),
                },
            )
            descriptions[maintop_no] = routine_description
        return descriptions

    def _ensure_completed_routines(self, routine_descriptions, today):
        routine_specs = [
            (
                "RD-HD-001",
                today - timedelta(days=9),
                6,
                "Lub oil pump inspection completed",
            ),
            ("RD-HD-002", today - timedelta(days=3), 4, "Relay calibration completed"),
        ]
        for maintop_no, completion_date, manpower, details in routine_specs:
            CompletedRoutine.objects.get_or_create(
                routine=routine_descriptions[maintop_no],
                completion_details=details,
                defaults={
                    "old_dart_number": "",
                    "new_dart_number": "",
                    "date_of_completion": completion_date,
                    "hours": 5,
                    "minutes": 30,
                    "total_manpower": manpower,
                    "trial_team": False,
                },
            )

    def _ensure_defects(self, department, equipment_names, today):
        defect_specs = [
            {
                "dart_number": "HD-DART-001",
                "equipment": equipment_names["Main Engine"],
                "component": "Fuel Pump Drive",
                "description": "Pressure fluctuation observed during harbour trial",
                "is_closed": False,
                "ops_status": False,
                "trial_required": False,
                "spares_required": True,
                "created_date": today - timedelta(days=6),
                "rectification_date": today + timedelta(days=4),
                "cmms_sync_status": False,
                "cmms_sync_date": today - timedelta(days=2),
            },
            {
                "dart_number": "HD-DART-002",
                "equipment": equipment_names["Steering Gear"],
                "component": "Hydraulic Actuator",
                "description": "Response lag during wheel over test",
                "is_closed": False,
                "ops_status": True,
                "trial_required": True,
                "spares_required": False,
                "created_date": today - timedelta(days=3),
                "rectification_date": today + timedelta(days=7),
                "cmms_sync_status": False,
                "cmms_sync_date": None,
            },
            {
                "dart_number": "HD-DART-003",
                "equipment": equipment_names["Ship Service Generator"],
                "component": "Cooling Water Pump",
                "description": "Seal leak rectified and post-maintenance checks completed",
                "is_closed": True,
                "ops_status": True,
                "trial_required": False,
                "spares_required": False,
                "created_date": today - timedelta(days=18),
                "rectification_date": today - timedelta(days=5),
                "cmms_sync_status": True,
                "cmms_sync_date": today - timedelta(days=4),
            },
            {
                "dart_number": "HD-DART-004",
                "equipment": equipment_names["Reduction Gear"],
                "component": "Bearing Temperature Sensor",
                "description": "Intermittent false high-temperature alarm",
                "is_closed": False,
                "ops_status": True,
                "trial_required": False,
                "spares_required": False,
                "created_date": today - timedelta(days=1),
                "rectification_date": today + timedelta(days=9),
                "cmms_sync_status": False,
                "cmms_sync_date": None,
            },
        ]
        defects = {}
        for spec in defect_specs:
            defect, _ = InitiateDart.objects.get_or_create(
                dart_number=spec["dart_number"],
                defaults={
                    "department_id": department,
                    "equipment_ems": spec["equipment"],
                    "dart_date": spec["created_date"],
                    "rectification_date": spec["rectification_date"],
                    "ops_status": spec["ops_status"],
                    "trial_required": spec["trial_required"],
                    "defective_component": spec["component"],
                    "defective_discriptions": spec["description"],
                    "is_closed": spec["is_closed"],
                    "sapres_required": spec["spares_required"],
                    "maintenance_period": "OPERATIONAL",
                    "cmms_sync_status": spec["cmms_sync_status"],
                    "cmms_sync_date": spec["cmms_sync_date"],
                },
            )
            InitiateDart.objects.filter(pk=defect.pk).update(
                department_id=department,
                equipment_ems=spec["equipment"],
                created_date=spec["created_date"],
                dart_date=spec["created_date"],
                rectification_date=spec["rectification_date"],
                ops_status=spec["ops_status"],
                trial_required=spec["trial_required"],
                defective_component=spec["component"],
                defective_discriptions=spec["description"],
                is_closed=spec["is_closed"],
                sapres_required=spec["spares_required"],
                maintenance_period="OPERATIONAL",
                cmms_sync_status=spec["cmms_sync_status"],
                cmms_sync_date=spec["cmms_sync_date"],
            )
            defects[spec["dart_number"]] = defect
        return defects

    def _ensure_completed_defects(self, defects, today):
        CompleteDefectDart.objects.get_or_create(
            dart_details=defects["HD-DART-003"],
            defaults={
                "serial_no": "HD-CD-001",
                "dart_no": "HD-DART-003",
                "rectified_date": today - timedelta(days=5),
                "days_delay": 1,
                "spares_delay": 0,
            },
        )

    def _ensure_spares(self, department):
        authority, _ = Authority.objects.get_or_create(name="HOME DASHBOARD AUTHORITY")
        denomination, _ = Denomination.objects.get_or_create(
            name="EA", department=department
        )
        spare_class, _ = SpareClass.objects.get_or_create(
            name="MECHANICAL", department=department
        )
        equipment_class, _ = EquipmentClass.objects.get_or_create(
            name="PROPULSION SYSTEM",
            spare_class=spare_class,
        )

        spare_specs = [
            ("HD-SPARE-001", "Fuel pump repair kit", True, 6, 0),
            ("HD-SPARE-002", "Generator relay card", False, 4, 2),
            ("HD-SPARE-003", "Hydraulic seal set", True, 8, 3),
        ]
        for pattern_number, description, critical, authorised, available in spare_specs:
            Spares.objects.update_or_create(
                pattern_number=pattern_number,
                defaults={
                    "equipment_class": equipment_class,
                    "description": description,
                    "category": Spares.CONSUMABLE,
                    "critical": critical,
                    "compartment": "ER-STORE",
                    "location": "MAIN STORE",
                    "rack_position": "A1",
                    "rack_number": "R1",
                    "denomination": denomination,
                    "quantity_authorised": authorised,
                    "quantity_available": available,
                    "authority": authority,
                    "is_obs": True,
                },
            )

    def _ensure_planner_activities(self, departments, ship, user, today):
        activity_specs = [
            (
                "Main engine inspection window",
                departments["ENG"],
                today,
                "active",
                55,
                timezone.datetime(2000, 1, 1, 0, 1).time(),
                timezone.datetime(2000, 1, 1, 23, 59).time(),
            ),
            (
                "Generator relay close-out",
                departments["ELE"],
                today - timedelta(days=1),
                "scheduled",
                20,
                timezone.datetime(2000, 1, 1, 9, 0).time(),
                timezone.datetime(2000, 1, 1, 11, 0).time(),
            ),
            (
                "Provision cold store restoration",
                departments["LOG"],
                today + timedelta(days=2),
                "scheduled",
                10,
                timezone.datetime(2000, 1, 1, 9, 0).time(),
                timezone.datetime(2000, 1, 1, 11, 0).time(),
            ),
        ]
        for (
            title,
            department,
            date_value,
            status,
            progress,
            start_time,
            end_time,
        ) in activity_specs:
            PlannerActivity.objects.update_or_create(
                title=title,
                date=date_value,
                defaults={
                    "subtitle": "HOME-DASHBOARD-DEMO",
                    "description": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "department": department,
                    "ship": ship,
                    "status": status,
                    "progress": progress,
                    "equipment": "HOME-DASHBOARD-DEMO",
                    "reference": "HOME-DASHBOARD-DEMO",
                    "created_by": user,
                },
            )

    def _ensure_tagout_workflow(self, user, ship_equipment, department, today):
        tagout_one, _ = TagOut.objects.get_or_create(
            tagout_description="HOME-DASHBOARD-DEMO-TAGOUT-1",
            defaults={
                "date": today,
                "user_profile": user,
                "tagout_equipment_name": ship_equipment,
                "name_of_subsystem": "Fuel Oil",
                "name_of_component": "Fuel Pump",
                "type": "danger",
                "condition": "non_ops",
                "approval_status": "in_progress",
                "expected_date_of_tagin": today + timedelta(days=4),
            },
        )
        tagout_one.departments_affected.set([department])

        tagout_two, _ = TagOut.objects.get_or_create(
            tagout_description="HOME-DASHBOARD-DEMO-TAGOUT-2",
            defaults={
                "date": today - timedelta(days=1),
                "user_profile": user,
                "tagout_equipment_name": ship_equipment,
                "name_of_subsystem": "Control",
                "name_of_component": "Relay Card",
                "type": "warning",
                "condition": "partially_ops",
                "approval_status": "approved",
                "expected_date_of_tagin": today + timedelta(days=2),
            },
        )
        tagout_two.departments_affected.set([department])

        TagIn.objects.update_or_create(
            tagout=tagout_two,
            defaults={
                "tagin_date": today,
                "tagin_description": "HOME-DASHBOARD-DEMO-TAGIN",
                "tagin_maintainer": "Demo Maintainer",
                "all_items_returned": False,
                "items_pending": "Awaiting QA check",
                "status": "pending",
                "approval_status": "pending",
            },
        )
