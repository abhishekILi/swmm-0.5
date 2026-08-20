#!/usr/bin/env python
"""
Standalone combined seeder — run directly with `python seed_all.py` from the
`backend/` directory (no `manage.py` needed).

Seeds demo data for:
  - Refit Maintenance dashboard (refit/dart/ems/obs tables)
  - DL Monitoring / DL history (dl_monitor tables: dl_tracking, dl2tracking,
    dl3tracking, dl_history)

Pass --flush to wipe previously seeded demo rows before reseeding.
"""

import os
import sys
from datetime import timedelta


def seed_refit_dashboard(flush=False):
    from dart.models import (
        CompleteDefectDart,
        CompletedRoutine,
        InitiateDart,
        InitiateRADL,
        RADLMaster,
    )
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils import timezone
    from ems.models import (
        AddRoutineDetails,
        EquipmentName,
        RoutineDescription,
        SectionName,
        UniqueRoutineName,
    )
    from master.models import Department
    from obs.models import (
        Authority,
        Denomination,
        EquipmentClass,
        RoutineSpareUsage,
        SpareClass,
        Spares,
    )
    from users.models import CustomUserProfile

    def _flush():
        RoutineSpareUsage.objects.filter(
            routine__maintop_no__startswith="RF-MT-"
        ).delete()
        Spares.objects.filter(pattern_number__startswith="RF-SPARE-").delete()
        InitiateRADL.objects.filter(dl_no__startswith="DL-REFIT-").delete()
        RADLMaster.objects.filter(ra_dl_name="REFIT-DASHBOARD-GROUP-1").delete()
        CompleteDefectDart.objects.filter(dart_no__startswith="RF-DART-").delete()
        InitiateDart.objects.filter(dart_number__startswith="RF-DART-").delete()
        CompletedRoutine.objects.filter(
            routine__maintop_no__startswith="RF-MT-"
        ).delete()
        RoutineDescription.objects.filter(maintop_no__startswith="RF-MT-").delete()
        AddRoutineDetails.objects.filter(maintop_no__startswith="RF-MT-").delete()
        print("Flushed previously seeded refit demo records.")

    def _ensure_departments():
        department_specs = [
            ("ME", "Mechanical Engineering"),
            ("EE", "Electrical Engineering"),
            ("LOG", "Logistics"),
            ("OPS", "Operations"),
        ]
        departments = {}
        for code, name in department_specs:
            department, _ = Department.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "dep_code": code,
                    "description": f"{name} refit dashboard demo department",
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

    def _ensure_user(username, department):
        user_model = get_user_model()

        profile, _ = CustomUserProfile.objects.get_or_create(
            personal_number="RF2001",
            defaults={
                "firstname": "Refit",
                "lastname": "Dashboard",
                "designation": "Refit Officer",
                "department": department,
                "section": "REFIT",
                "has_credentials": True,
            },
        )
        if profile.department_id != department.id:
            profile.department = department
            profile.save(update_fields=["department"])

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"user_profile": profile},
        )
        if user.user_profile_id != profile.id:
            user.user_profile = profile
            user.save(update_fields=["user_profile"])
        if created:
            user.set_password("Pass@12345")
            user.save(update_fields=["password"])
        return user

    def _ensure_sections(departments):
        section_specs = [
            ("Hull Department", departments["ME"]),
            ("Propulsion Department", departments["ME"]),
            ("Combat Systems", departments["EE"]),
            ("Logistics Support", departments["LOG"]),
            ("Trial Coordination", departments["OPS"]),
        ]
        sections = {}
        for name, department in section_specs:
            section, _ = SectionName.objects.get_or_create(
                name=name, department=department
            )
            sections[name] = section
        return sections

    def _ensure_equipment(sections):
        equipment_specs = [
            (
                "Hull Dock & Boarding",
                sections["Hull Department"],
                180.0,
                "INACTIVE",
                "HULL-RF-001",
            ),
            (
                "Propulsion Shafting",
                sections["Propulsion Department"],
                320.0,
                "INACTIVE",
                "PROP-RF-001",
            ),
            (
                "Weapons & Sensors P22",
                sections["Combat Systems"],
                410.0,
                "INACTIVE",
                "COMBAT-RF-001",
            ),
            (
                "Dockyard Support Console",
                sections["Logistics Support"],
                95.0,
                "INACTIVE",
                "LOG-RF-001",
            ),
            (
                "Trial Acceptance Panel",
                sections["Trial Coordination"],
                140.0,
                "INACTIVE",
                "OPS-RF-001",
            ),
            (
                "Main Diesel Generator",
                sections["Propulsion Department"],
                250.0,
                "INACTIVE",
                "ENG-RF-002",
            ),
            ("AC Plant", sections["Hull Department"], 150.0, "INACTIVE", "ENG-RF-003"),
            (
                "Navigation Radar",
                sections["Combat Systems"],
                180.0,
                "INACTIVE",
                "ELE-RF-002",
            ),
            (
                "Communication System",
                sections["Combat Systems"],
                200.0,
                "INACTIVE",
                "ELE-RF-003",
            ),
            (
                "Fire Fighting System",
                sections["Hull Department"],
                120.0,
                "INACTIVE",
                "HULL-RF-002",
            ),
        ]
        equipment_map = {}
        for name, section, rhsi, state, code in equipment_specs:
            equipment, _ = EquipmentName.objects.get_or_create(
                name=name,
                section=section,
                defaults={
                    "nomenclature": name.upper(),
                    "equipment_code": code,
                    "rhsi": rhsi,
                    "state": state,
                    "started_at_location": "AT HARBOUR",
                },
            )
            updates = []
            if equipment.section_id != section.id:
                equipment.section = section
                updates.append("section")
            if equipment.nomenclature != name.upper():
                equipment.nomenclature = name.upper()
                updates.append("nomenclature")
            if equipment.equipment_code != code:
                equipment.equipment_code = code
                updates.append("equipment_code")
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
            equipment_map[name] = equipment
        return equipment_map

    def _ensure_routine_names():
        names = {}
        for name in ["SHORT REFIT", "NORMAL REFIT", "MAJOR REFIT"]:
            routine_name, _ = UniqueRoutineName.objects.get_or_create(name=name)
            names[name] = routine_name
        return names

    def _ensure_refit_routines(equipment, routine_names, now):
        routine_specs = [
            {
                "maintop_no": "RF-MT-001",
                "routine_no": "RF-R-001",
                "equipment": equipment["Hull Dock & Boarding"],
                "routine_name": routine_names["SHORT REFIT"],
                "frequency": "6 MONTHS",
                "months": 6,
                "hours": 300,
                "converted": True,
                "remarks": "Docking readiness routine",
            },
            {
                "maintop_no": "RF-MT-002",
                "routine_no": "RF-R-002",
                "equipment": equipment["Propulsion Shafting"],
                "routine_name": routine_names["NORMAL REFIT"],
                "frequency": "12 MONTHS",
                "months": 12,
                "hours": 500,
                "converted": False,
                "remarks": "Shaft alignment routine",
            },
            {
                "maintop_no": "RF-MT-003",
                "routine_no": "RF-R-003",
                "equipment": equipment["Weapons & Sensors P22"],
                "routine_name": routine_names["MAJOR REFIT"],
                "frequency": "18 MONTHS",
                "months": 18,
                "hours": 800,
                "converted": True,
                "remarks": "Combat system overhaul",
            },
            {
                "maintop_no": "RF-MT-004",
                "routine_no": "RF-R-004",
                "equipment": equipment["Trial Acceptance Panel"],
                "routine_name": routine_names["SHORT REFIT"],
                "frequency": "6 MONTHS",
                "months": 6,
                "hours": 220,
                "converted": False,
                "remarks": "Acceptance readiness checks",
            },
            {
                "maintop_no": "RF-MT-005",
                "routine_no": "RF-R-005",
                "equipment": equipment["Main Diesel Generator"],
                "routine_name": routine_names["MAJOR REFIT"],
                "frequency": "24 MONTHS",
                "months": 24,
                "hours": 1200,
                "converted": True,
                "remarks": "Major overhaul of diesel generator",
            },
            {
                "maintop_no": "RF-MT-006",
                "routine_no": "RF-R-006",
                "equipment": equipment["AC Plant"],
                "routine_name": routine_names["NORMAL REFIT"],
                "frequency": "12 MONTHS",
                "months": 12,
                "hours": 600,
                "converted": True,
                "remarks": "Routine AC plant servicing",
            },
            {
                "maintop_no": "RF-MT-007",
                "routine_no": "RF-R-007",
                "equipment": equipment["Navigation Radar"],
                "routine_name": routine_names["SHORT REFIT"],
                "frequency": "6 MONTHS",
                "months": 6,
                "hours": 300,
                "converted": False,
                "remarks": "Radar alignment checks",
            },
            {
                "maintop_no": "RF-MT-008",
                "routine_no": "RF-R-008",
                "equipment": equipment["Communication System"],
                "routine_name": routine_names["NORMAL REFIT"],
                "frequency": "12 MONTHS",
                "months": 12,
                "hours": 450,
                "converted": True,
                "remarks": "Comm system diagnostics",
            },
            {
                "maintop_no": "RF-MT-009",
                "routine_no": "RF-R-009",
                "equipment": equipment["Fire Fighting System"],
                "routine_name": routine_names["MAJOR REFIT"],
                "frequency": "18 MONTHS",
                "months": 18,
                "hours": 800,
                "converted": False,
                "remarks": "Fire fighting system pressure test",
            },
            {
                "maintop_no": "RF-MT-010",
                "routine_no": "RF-R-010",
                "equipment": equipment["Dockyard Support Console"],
                "routine_name": routine_names["SHORT REFIT"],
                "frequency": "6 MONTHS",
                "months": 6,
                "hours": 200,
                "converted": True,
                "remarks": "Console functionality check",
            },
        ]
        routines = {}
        for index, spec in enumerate(routine_specs, start=1):
            routine, _ = AddRoutineDetails.objects.get_or_create(
                maintop_no=spec["maintop_no"],
                equipment_name=spec["equipment"],
                routine_name=spec["routine_name"],
                defaults={
                    "routine_no": spec["routine_no"],
                    "equipment_code": spec["equipment"].equipment_code,
                    "nomenclature": spec["equipment"].nomenclature,
                    "by_whom": "DYD",
                    "frequency": spec["frequency"],
                    "frequency_in_months": spec["months"],
                    "frequency_in_hours": spec["hours"],
                    "last_routine_completion_date": now - timedelta(days=index * 18),
                    "last_routine_completion_atrunning_hrs": float(spec["hours"]),
                    "routine_category": "ALTERNATE PERIODIC",
                    "remarks": spec["remarks"],
                    "converted": spec["converted"],
                    "converted_at": (
                        now - timedelta(days=index * 5) if spec["converted"] else None
                    ),
                },
            )
            updates = {
                "routine_no": spec["routine_no"],
                "equipment_code": spec["equipment"].equipment_code,
                "nomenclature": spec["equipment"].nomenclature,
                "by_whom": "DYD",
                "frequency": spec["frequency"],
                "frequency_in_months": spec["months"],
                "frequency_in_hours": spec["hours"],
                "last_routine_completion_date": now - timedelta(days=index * 18),
                "last_routine_completion_atrunning_hrs": float(spec["hours"]),
                "routine_category": "ALTERNATE PERIODIC",
                "remarks": spec["remarks"],
                "converted": spec["converted"],
                "converted_at": (
                    now - timedelta(days=index * 5) if spec["converted"] else None
                ),
            }
            AddRoutineDetails.objects.filter(pk=routine.pk).update(**updates)
            routine.refresh_from_db()
            routines[spec["maintop_no"]] = routine
        return routines

    def _ensure_routine_descriptions(routines, today):
        description_specs = [
            (
                "RF-MT-001",
                "Inspect hull closure and boarding arrangements",
                today + timedelta(days=4),
                today - timedelta(days=25),
            ),
            (
                "RF-MT-002",
                "Carry out shaft alignment and lubrication verification",
                today + timedelta(days=8),
                today - timedelta(days=32),
            ),
            (
                "RF-MT-003",
                "Overhaul weapons and sensor calibration loop",
                today + timedelta(days=12),
                today - timedelta(days=41),
            ),
            (
                "RF-MT-004",
                "Validate trial panel acceptance interlocks",
                today + timedelta(days=6),
                today - timedelta(days=19),
            ),
            (
                "RF-MT-005",
                "Dismantle and inspect diesel generator pistons",
                today + timedelta(days=10),
                today - timedelta(days=50),
            ),
            (
                "RF-MT-006",
                "Clean AC plant coils and check refrigerant levels",
                today + timedelta(days=5),
                today - timedelta(days=15),
            ),
            (
                "RF-MT-007",
                "Recalibrate navigation radar antennas",
                today + timedelta(days=14),
                today - timedelta(days=30),
            ),
            (
                "RF-MT-008",
                "Test communication system signal strength",
                today + timedelta(days=7),
                today - timedelta(days=22),
            ),
            (
                "RF-MT-009",
                "Hydro-test fire fighting system pipelines",
                today + timedelta(days=20),
                today - timedelta(days=60),
            ),
            (
                "RF-MT-010",
                "Verify dockyard support console indicators",
                today + timedelta(days=3),
                today - timedelta(days=10),
            ),
        ]
        descriptions = {}
        for maintop_no, text, due_date, previous_date in description_specs:
            routine = routines[maintop_no]
            department = (
                routine.equipment_name.section.department
                if routine.equipment_name.section
                else None
            )
            description, _ = RoutineDescription.objects.get_or_create(
                add_routine_details=routine,
                routine_no=routine.routine_no or maintop_no,
                defaults={
                    "equipment_name": routine.equipment_name,
                    "routine_name": routine.routine_name,
                    "maintop_no": maintop_no,
                    "routine_description": text,
                    "by_whom": "DYD",
                    "due_date": due_date,
                    "previous_completed_date": previous_date,
                    "department_f_key": department,
                },
            )
            updates = {
                "equipment_name": routine.equipment_name,
                "routine_name": routine.routine_name,
                "maintop_no": maintop_no,
                "routine_description": text,
                "by_whom": "DYD",
                "due_date": due_date,
                "previous_completed_date": previous_date,
                "department_f_key": department,
            }
            RoutineDescription.objects.filter(pk=description.pk).update(**updates)
            description.refresh_from_db()
            descriptions[maintop_no] = description
        return descriptions

    def _ensure_completed_routines(descriptions, today):
        completed_specs = [
            (
                "RF-MT-001",
                today - timedelta(days=4),
                8,
                "Hull docking checks completed",
            ),
            ("RF-MT-003", today - timedelta(days=2), 6, "Sensor overhaul completed"),
        ]
        for maintop_no, completion_date, manpower, details in completed_specs:
            CompletedRoutine.objects.get_or_create(
                routine=descriptions[maintop_no],
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

    def _ensure_refit_defects(department, equipment, today):
        defect_specs = [
            {
                "dart_number": "RF-DART-001",
                "equipment": equipment["Hull Dock & Boarding"],
                "component": "Hull Plate Section A",
                "description": "Docking hull section pending contractor clearance",
                "trial_required": False,
                "spares_required": True,
                "is_closed": False,
                "occasion": "RC. Refit Commencement",
                "rectification": today + timedelta(days=3),
            },
            {
                "dart_number": "RF-DART-002",
                "equipment": equipment["Propulsion Shafting"],
                "component": "Shaft Alignment Pack",
                "description": "Propulsion shaft alignment under restoration",
                "trial_required": True,
                "spares_required": False,
                "is_closed": False,
                "occasion": "C2. Machinery Opening-Up",
                "rectification": today + timedelta(days=7),
            },
            {
                "dart_number": "RF-DART-003",
                "equipment": equipment["Weapons & Sensors P22"],
                "component": "Weapons Interface Rack",
                "description": "Combat system rectification completed and awaiting acceptance note",
                "trial_required": True,
                "spares_required": False,
                "is_closed": True,
                "occasion": "C3. Defect Rectification & Refit",
                "rectification": today - timedelta(days=1),
            },
            {
                "dart_number": "RF-DART-004",
                "equipment": equipment["Trial Acceptance Panel"],
                "component": "Acceptance Logic Board",
                "description": "QA trial schedule aligned with acceptance window",
                "trial_required": True,
                "spares_required": False,
                "is_closed": True,
                "occasion": "Acceptance Readiness",
                "rectification": today - timedelta(days=3),
            },
            {
                "dart_number": "RF-DART-005",
                "equipment": equipment["Main Diesel Generator"],
                "component": "Fuel Injector Pump",
                "description": "Fuel injector pump requires calibration and testing",
                "trial_required": True,
                "spares_required": True,
                "is_closed": False,
                "occasion": "C2. Machinery Opening-Up",
                "rectification": today + timedelta(days=5),
            },
            {
                "dart_number": "RF-DART-006",
                "equipment": equipment["AC Plant"],
                "component": "Compressor Motor",
                "description": "Compressor motor overheating during continuous operation",
                "trial_required": True,
                "spares_required": False,
                "is_closed": False,
                "occasion": "C3. Defect Rectification & Refit",
                "rectification": today + timedelta(days=2),
            },
            {
                "dart_number": "RF-DART-007",
                "equipment": equipment["Navigation Radar"],
                "component": "Antenna Motor Drive",
                "description": "Antenna motor drive erratic rotation",
                "trial_required": True,
                "spares_required": True,
                "is_closed": False,
                "occasion": "RC. Refit Commencement",
                "rectification": today + timedelta(days=8),
            },
            {
                "dart_number": "RF-DART-008",
                "equipment": equipment["Communication System"],
                "component": "VHF Transceiver",
                "description": "VHF transceiver module replacement",
                "trial_required": True,
                "spares_required": False,
                "is_closed": True,
                "occasion": "C4. Boxing-Up & Harbour Trials",
                "rectification": today - timedelta(days=2),
            },
            {
                "dart_number": "RF-DART-009",
                "equipment": equipment["Fire Fighting System"],
                "component": "Main Fire Pump",
                "description": "Main fire pump seal leakage",
                "trial_required": True,
                "spares_required": True,
                "is_closed": False,
                "occasion": "C3. Defect Rectification & Refit",
                "rectification": today + timedelta(days=4),
            },
            {
                "dart_number": "RF-DART-010",
                "equipment": equipment["Dockyard Support Console"],
                "component": "Power Supply Unit",
                "description": "Power supply unit failure, needs replacement",
                "trial_required": False,
                "spares_required": True,
                "is_closed": True,
                "occasion": "RC. Refit Commencement",
                "rectification": today - timedelta(days=5),
            },
        ]
        defects = {}
        for spec in defect_specs:
            defect, _ = InitiateDart.objects.get_or_create(
                dart_number=spec["dart_number"],
                defaults={
                    "department_id": department,
                    "equipment_ems": spec["equipment"],
                    "maintenance_period": "REFIT",
                    "dart_occasion": spec["occasion"],
                    "dart_date": today - timedelta(days=10),
                    "rectification_date": spec["rectification"],
                    "ops_status": True,
                    "trial_required": spec["trial_required"],
                    "defective_component": spec["component"],
                    "defective_discriptions": spec["description"],
                    "is_closed": spec["is_closed"],
                    "sapres_required": spec["spares_required"],
                },
            )
            InitiateDart.objects.filter(pk=defect.pk).update(
                department_id=department,
                equipment_ems=spec["equipment"],
                maintenance_period="REFIT",
                dart_occasion=spec["occasion"],
                dart_date=today - timedelta(days=10),
                rectification_date=spec["rectification"],
                ops_status=True,
                trial_required=spec["trial_required"],
                defective_component=spec["component"],
                defective_discriptions=spec["description"],
                is_closed=spec["is_closed"],
                sapres_required=spec["spares_required"],
            )
            defect.refresh_from_db()
            defects[spec["dart_number"]] = defect
        return defects

    def _ensure_completed_defects(defects, today):
        CompleteDefectDart.objects.get_or_create(
            dart_details=defects["RF-DART-003"],
            defaults={
                "serial_no": "RF-CD-001",
                "dart_no": "RF-DART-003",
                "rectified_date": today - timedelta(days=1),
                "days_delay": 2,
                "spares_delay": 0,
            },
        )
        CompleteDefectDart.objects.get_or_create(
            dart_details=defects["RF-DART-004"],
            defaults={
                "serial_no": "RF-CD-002",
                "dart_no": "RF-DART-004",
                "rectified_date": today - timedelta(days=3),
                "days_delay": 0,
                "spares_delay": 0,
            },
        )

    def _ensure_dl_entries(defects):
        radl_master, _ = RADLMaster.objects.get_or_create(
            ra_dl_name="REFIT-DASHBOARD-GROUP-1",
            defaults={
                "dockyard_name": "Naval Dockyard",
                "refit_type_name": "NORMAL REFIT",
            },
        )
        entry_specs = [
            ("RF-DART-001", "DL-REFIT-001", "DL-II", "GENERATED", "RF-GRP-1"),
            ("RF-DART-002", "DL-REFIT-002", "RA", "DRAFT", "RF-GRP-2"),
            ("RF-DART-003", "DL-REFIT-003", "DL-III", "APPROVED", "RF-GRP-3"),
        ]
        for dart_number, dl_no, dl_type, status, group_id in entry_specs:
            InitiateRADL.objects.get_or_create(
                initiate_dart=defects[dart_number],
                dl_no=dl_no,
                defaults={
                    "radl_master": radl_master,
                    "status": status,
                    "dl_type": dl_type,
                    "dl_key": dl_no,
                    "ra_grup_id": group_id,
                    "remarks": "Refit dashboard demo DL entry",
                    "additional_remarks": "",
                    "is_active": status in {"GENERATED", "APPROVED"},
                },
            )

    def _ensure_spares(department):
        authority, _ = Authority.objects.get_or_create(name="REFIT DASHBOARD AUTHORITY")
        denomination, _ = Denomination.objects.get_or_create(
            name="EA", department=department
        )
        spare_class, _ = SpareClass.objects.get_or_create(
            name="REFIT SPARES", department=department
        )
        equipment_class, _ = EquipmentClass.objects.get_or_create(
            name="REFIT SUPPORT SYSTEMS", spare_class=spare_class
        )
        spare_specs = [
            ("RF-SPARE-001", "HULL SEAL KIT", True, 4, 0),
            ("RF-SPARE-002", "SHAFT ALIGNMENT TOOL", False, 2, 1),
            ("RF-SPARE-003", "SENSOR CALIBRATION PACK", True, 3, 0),
        ]
        spare_map = {}
        for pattern_number, description, critical, authorised, available in spare_specs:
            spare, _ = Spares.objects.update_or_create(
                pattern_number=pattern_number,
                defaults={
                    "equipment_class": equipment_class,
                    "description": description,
                    "category": Spares.CONSUMABLE,
                    "critical": critical,
                    "compartment": "REFIT-STORE",
                    "location": "DOCKYARD STORE",
                    "rack_position": "A1",
                    "rack_number": "R1",
                    "denomination": denomination,
                    "quantity_authorised": authorised,
                    "quantity_available": available,
                    "authority": authority,
                    "is_obs": True,
                },
            )
            spare_map[pattern_number] = spare
        return spare_map

    def _ensure_routine_spare_usages(routines, descriptions, spare_map):
        usage_specs = [
            ("RF-MT-001", "RF-SPARE-001", "2.00"),
            ("RF-MT-003", "RF-SPARE-003", "1.00"),
        ]
        for maintop_no, pattern_number, quantity in usage_specs:
            RoutineSpareUsage.objects.get_or_create(
                routine=routines[maintop_no],
                routine_description=descriptions[maintop_no],
                spare=spare_map[pattern_number],
                defaults={"quantity_used": quantity},
            )

    with transaction.atomic():
        today = timezone.localdate()
        now = timezone.now()

        if flush:
            _flush()

        departments = _ensure_departments()
        sections = _ensure_sections(departments)
        equipment = _ensure_equipment(sections)
        routine_names = _ensure_routine_names()
        routines = _ensure_refit_routines(equipment, routine_names, now)
        descriptions = _ensure_routine_descriptions(routines, today)
        _ensure_completed_routines(descriptions, today)

        demo_department = departments["OPS"]
        user = _ensure_user("refit.dashboard.demo", demo_department)

        for dep in departments.values():
            defects = _ensure_refit_defects(dep, equipment, today)
            _ensure_completed_defects(defects, today)
            _ensure_dl_entries(defects)
            spare_map = _ensure_spares(dep)
            _ensure_routine_spare_usages(routines, descriptions, spare_map)

        print(
            "Refit dashboard demo data is ready: routines, descriptions, defects, "
            "completed routines, DL entries, and spare dependencies."
        )
        print(
            f"Demo login user '{user.username}' (password: Pass@12345) is scoped to "
            f"department '{demo_department.name}' for dashboard/defect filtering."
        )


def seed_dl_monitor(flush=False):
    from django.db import transaction
    from django.utils import timezone
    from dl_monitor.models import DLClose, DLTracker
    from master.models import Department, SubDepartment

    # Real login accounts in this DB (ADMIN, SHIPADMIN, CO, 1234, refit.dashboard.demo)
    # all belong to the "Operations" department, so seeded trackers are attached there —
    # otherwise the DL1/DL2/DL3 tracking endpoints (which filter by
    # request.user.user_profile.department.id via sub_dept_id__department_name) would
    # seed data invisible to whoever is actually logged in during manual testing.
    department_code = "OPS"

    def _flush():
        DLTracker.objects.filter(defect_no__startswith="DL-MON-").delete()
        print("Flushed previously seeded DL monitor demo records.")

    def _ensure_department():
        department, _ = Department.objects.get_or_create(code=department_code)
        return department

    def _ensure_sub_departments(department):
        specs = ["SubDept Operations", "Bridge"]
        sub_departments = {}
        for name in specs:
            sub_department, _ = SubDepartment.objects.get_or_create(
                name=name,
                department_name=department,
                defaults={"code": name[:3].upper(), "active": True},
            )
            sub_departments[name] = sub_department
        return sub_departments

    def _ensure_trackers(sub_departments, specs, is_closed):
        trackers = {}
        for index, spec in enumerate(specs, start=1):
            common_fields = {
                "sub_dept_id": sub_departments[spec["sub_department"]],
                "dl_type": spec["dl_type"],
                "equip_name": spec["equip_name"],
                "dart_no": spec["dart_no"],
                "defect_description": spec["defect_description"],
                "ship_remarks": spec["ship_remarks"],
                "yard_remarks": spec["yard_remarks"],
                "status": spec["status"],
                "critical": spec["critical"],
                "is_closed": is_closed,
            }
            tracker, _ = DLTracker.objects.get_or_create(
                defect_no=spec["defect_no"],
                defaults={
                    **common_fields,
                    "current_status_updated_on": timezone.now() - timedelta(days=index),
                },
            )
            DLTracker.objects.filter(pk=tracker.pk).update(**common_fields)
            tracker.refresh_from_db()
            trackers[spec["defect_no"]] = tracker
        return trackers

    def _ensure_open_trackers(sub_departments):
        # DL1/DL2/DL3 rows with is_closed=False — matches the exact filter used by
        # DLTrackingAPIView / DL2TrackingAPIView / DL3TrackingAPIView.
        specs = [
            {
                "defect_no": "DL-MON-001",
                "dl_type": "DL1",
                "sub_department": "SubDept Operations",
                "equip_name": "Hull Dock & Boarding",
                "dart_no": "RF-DART-001",
                "defect_description": "Hull section coating damage found during docking survey",
                "ship_remarks": "Requires dockyard rectification",
                "yard_remarks": "Scheduled for next dock period",
                "status": "In Progress",
                "critical": True,
            },
            {
                "defect_no": "DL-MON-002",
                "dl_type": "DL1",
                "sub_department": "Bridge",
                "equip_name": "Navigation Radar",
                "dart_no": "RF-DART-007",
                "defect_description": "Antenna motor drive erratic rotation",
                "ship_remarks": "Awaiting spare confirmation",
                "yard_remarks": "Yard survey pending",
                "status": "Not yet started",
                "critical": False,
            },
            {
                "defect_no": "DL-MON-003",
                "dl_type": "DL2",
                "sub_department": "SubDept Operations",
                "equip_name": "Propulsion Shafting",
                "dart_no": "RF-DART-002",
                "defect_description": "Shaft alignment drift beyond tolerance",
                "ship_remarks": "Awaiting yard confirmation",
                "yard_remarks": "Alignment tooling mobilised",
                "status": "In Progress",
                "critical": False,
            },
            {
                "defect_no": "DL-MON-004",
                "dl_type": "DL2",
                "sub_department": "Bridge",
                "equip_name": "Communication System",
                "dart_no": "RF-DART-008",
                "defect_description": "VHF transceiver module replacement in progress",
                "ship_remarks": "Module removed for bench test",
                "yard_remarks": "Replacement module on order",
                "status": "In Progress",
                "critical": False,
            },
            {
                "defect_no": "DL-MON-005",
                "dl_type": "DL3",
                "sub_department": "SubDept Operations",
                "equip_name": "Weapons & Sensors P22",
                "dart_no": "RF-DART-003",
                "defect_description": "Sensor calibration loop fault under review",
                "ship_remarks": "Calibration in progress onboard",
                "yard_remarks": "Awaiting acceptance note",
                "status": "In Progress",
                "critical": True,
            },
            {
                "defect_no": "DL-MON-006",
                "dl_type": "DL3",
                "sub_department": "Bridge",
                "equip_name": "Main Diesel Generator",
                "dart_no": "RF-DART-005",
                "defect_description": "Fuel injector pump calibration pending",
                "ship_remarks": "Injector removed for testing",
                "yard_remarks": "Test bench booked",
                "status": "Not yet started",
                "critical": False,
            },
        ]
        return _ensure_trackers(sub_departments, specs, is_closed=False)

    def _ensure_closed_trackers(sub_departments):
        # Rows with is_closed=True, paired with a DLClose row so they show up on
        # dl_history (which reads DLClose regardless of department/dl_type).
        specs = [
            {
                "defect_no": "DL-MON-101",
                "dl_type": "DL1",
                "sub_department": "SubDept Operations",
                "equip_name": "Fire Fighting System",
                "dart_no": "RF-DART-009",
                "defect_description": "Main fire pump seal leakage rectified",
                "ship_remarks": "Seal replaced and pressure tested",
                "yard_remarks": "Acceptance note issued",
                "status": "Closed",
                "critical": True,
            },
            {
                "defect_no": "DL-MON-102",
                "dl_type": "DL2",
                "sub_department": "Bridge",
                "equip_name": "AC Plant",
                "dart_no": "RF-DART-006",
                "defect_description": "Compressor motor overheating fault closed",
                "ship_remarks": "Motor replaced",
                "yard_remarks": "Trial run satisfactory",
                "status": "Closed",
                "critical": False,
            },
            {
                "defect_no": "DL-MON-103",
                "dl_type": "DL3",
                "sub_department": "SubDept Operations",
                "equip_name": "Dockyard Support Console",
                "dart_no": "RF-DART-010",
                "defect_description": "Power supply unit failure resolved",
                "ship_remarks": "Unit replaced",
                "yard_remarks": "Closed after trial",
                "status": "Closed",
                "critical": False,
            },
        ]
        return _ensure_trackers(sub_departments, specs, is_closed=True)

    def _ensure_closed_history(trackers, today):
        history_specs = [
            (
                "DL-MON-101",
                today - timedelta(days=20),
                today - timedelta(days=18),
                today - timedelta(days=5),
            ),
            (
                "DL-MON-102",
                today - timedelta(days=15),
                today - timedelta(days=12),
                today - timedelta(days=3),
            ),
            (
                "DL-MON-103",
                today - timedelta(days=30),
                today - timedelta(days=27),
                today - timedelta(days=10),
            ),
        ]
        for defect_no, er_date, start_date, complete_date in history_specs:
            DLClose.objects.get_or_create(
                dl_tracker=trackers[defect_no],
                defaults={
                    "er_date_by_yard": er_date,
                    "start_work_by_yard": start_date,
                    "complete_work_by_yard": complete_date,
                },
            )

    with transaction.atomic():
        today = timezone.localdate()

        if flush:
            _flush()

        department = _ensure_department()
        sub_departments = _ensure_sub_departments(department)
        open_trackers = _ensure_open_trackers(sub_departments)
        closed_trackers = _ensure_closed_trackers(sub_departments)
        _ensure_closed_history(closed_trackers, today)

        print(
            f"DL monitor demo data is ready under department '{department.name}': "
            f"{len(open_trackers)} open DL1/DL2/DL3 trackers (visible on dl_tracking / "
            f"dl2tracking / dl3tracking) and {len(closed_trackers)} closed trackers with "
            f"DLClose history entries (visible on dl_history)."
        )


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swmm.settings")

    import django

    django.setup()

    flush = "--flush" in sys.argv[1:]

    print("== Seeding Refit Maintenance dashboard data ==")
    seed_refit_dashboard(flush=flush)

    print("\n== Seeding DL Monitoring / DL history data ==")
    seed_dl_monitor(flush=flush)

    print("\nAll done.")


if __name__ == "__main__":
    main()
