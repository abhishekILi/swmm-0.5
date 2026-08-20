from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from openpyxl import Workbook
from rest_framework import status
from rest_framework.test import APITestCase

from dart.models import DartSpare, InitiateDart
from ems.models import (
    AddRoutineDetails,
    EquipmentName,
    PlannedRoutineDescription,
    RoutineDescription,
    UniqueRoutineName,
)
from ilms.models import Item
from master.models import Department, MShipCommand, Ship, UnitType
from sfd.models import ShipEquipment
from wlms.models import (
    PlannedSparesDescription,
    PlannedWEDSpareList,
    SpareDataMap,
    WLMSEquipment,
    WLMSSpare,
)

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


class OnboardSparesFlowTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="store-user",
            password="Pass@12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.department = Department.objects.create(
            name="Engineering",
            code="ENG",
        )
        self.command = MShipCommand.objects.create(
            command_id=1,
            command_code="WNC",
            command_name="Western Naval Command",
            active=True,
        )
        self.unit_type = UnitType.objects.create(name="Ship")
        self.ship = Ship.objects.create(
            code="SHIP-30",
            name="Test Ship",
            command=self.command,
            unit_type=self.unit_type,
        )
        self.equipment = EquipmentName.objects.create(
            name="Main Generator",
            equipment_code="EQ-40",
        )
        self.ship_equipment = ShipEquipment.objects.create(
            nomenclature="Main Generator",
            equipment_serial_no="SER-40",
        )
        self.routine_name = UniqueRoutineName.objects.create(
            name="Quarterly Generator Routine",
        )
        self.routine = AddRoutineDetails.objects.create(
            equipment_name=self.equipment,
            routine_name=self.routine_name,
            routine_no="RT-50",
        )
        self.routine_description = RoutineDescription.objects.create(
            equipment_name=self.equipment,
            routine_name=self.routine_name,
            add_routine_details=self.routine,
            routine_no="RT-50",
            routine_description="Inspect and service the main generator.",
            by_whom="Engineering Department",
        )
        self.planned_routine_description = PlannedRoutineDescription.objects.create(
            routine_description_id=self.routine_description,
            spares_required=True,
        )
        self.spare_class = SpareClass.objects.create(
            name="mechanical",
            department=self.department,
        )
        self.equipment_class = EquipmentClass.objects.create(
            name="generator spares",
            spare_class=self.spare_class,
        )
        self.denomination = Denomination.objects.create(
            name="nos",
            department=self.department,
        )
        self.authority = Authority.objects.create(name="mo")
        self.spare = Spares.objects.create(
            equipment_class=self.equipment_class,
            pattern_number="pn-1001",
            description="fuel pump kit",
            category=Spares.PERMANENT,
            critical=True,
            compartment="engine room",
            location="store a",
            rack_position="r1",
            rack_number="rack-01",
            denomination=self.denomination,
            quantity_authorised=10,
            quantity_available=8,
            authority=self.authority,
            page="12",
            line="4",
            remarks="critical dg spare",
            mo_demand_number="mod-4582",
            is_obs=True,
        )

    def test_master_and_spare_fields_follow_reference_obs_structure(self):
        self.spare.refresh_from_db()

        self.assertEqual(self.spare_class.name, "MECHANICAL")
        self.assertEqual(self.equipment_class.name, "GENERATOR SPARES")
        self.assertEqual(self.denomination.name, "NOS")
        self.assertEqual(self.authority.name, "MO")
        self.assertEqual(self.spare.pattern_number, "PN-1001")
        self.assertEqual(self.spare.description, "FUEL PUMP KIT")
        self.assertEqual(self.spare.mo_demand_number, "MOD-4582")
        self.assertTrue(self.spare.is_obs)

    def test_available_quantity_cannot_cross_authorised_quantity(self):
        spare = Spares(
            equipment_class=self.equipment_class,
            pattern_number="PN-2001",
            description="Servo Assembly",
            denomination=self.denomination,
            quantity_authorised=2,
            quantity_available=3,
            authority=self.authority,
        )

        with self.assertRaises(ValidationError):
            spare.full_clean()

    def test_issue_list_and_return_update_onboard_quantity(self):
        issue = Issue.objects.create(
            spare=self.spare,
            equipment=self.equipment,
            username=self.user,
            quantity_issued=3,
            remarks="issued to maintainer",
            dart_number="dart-11",
        )
        IssueList.objects.create(
            issue_entry=issue,
            quantity_toreturn=2,
            dart_number="dart-11",
        )

        self.assertEqual(issue.equipment, self.equipment)
        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 5)

        return_entry = Return.objects.create(
            spare_id=self.spare,
            command_id=self.command,
            ship=self.ship,
            username="store-user",
            quantity_returned=2,
            remarks="returned from maintainer",
        )

        self.assertEqual(return_entry.ship, self.ship)
        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 7)

    def test_issue_above_available_stock_keeps_inventory_unchanged(self):
        with self.assertRaises(ValidationError):
            Issue.objects.create(
                spare=self.spare,
                equipment=self.equipment,
                username=self.user,
                quantity_issued=9,
            )

        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 8)
        self.assertFalse(Issue.objects.filter(spare=self.spare).exists())

    def test_editing_stock_movements_does_not_apply_quantity_twice(self):
        issue = Issue.objects.create(
            spare=self.spare,
            equipment=self.equipment,
            username=self.user,
            quantity_issued=2,
        )
        issue.remarks = "issued against maintenance"
        issue.save(update_fields=["remarks"])

        return_entry = Return.objects.create(
            spare_id=self.spare,
            quantity_returned=1,
        )
        return_entry.remarks = "returned unused"
        return_entry.save(update_fields=["remarks"])

        receive = PostReceive.objects.create(
            spare=self.spare,
            quantity_received=3,
            receipt_number="rec-atomic-01",
        )
        receive.remarks = "receipt verified"
        receive.save(update_fields=["remarks"])

        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 10)

    def test_return_cannot_raise_stock_above_authorised_quantity(self):
        with self.assertRaises(ValidationError):
            Return.objects.create(
                spare_id=self.spare,
                quantity_returned=3,
            )

        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 8)
        self.assertFalse(Return.objects.filter(spare_id=self.spare).exists())

    def test_receive_cannot_raise_stock_above_authorised_quantity(self):
        with self.assertRaises(ValidationError):
            PostReceive.objects.create(
                spare=self.spare,
                quantity_received=3,
                receipt_number="rec-over-limit",
            )

        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 8)
        self.assertFalse(PostReceive.objects.filter(spare=self.spare).exists())

    def test_anonymous_user_cannot_access_inventory(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/v1/onboard-spares/spares/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_change_inventory(self):
        viewer = get_user_model().objects.create_user(
            username="inventory-viewer",
            password="Pass@12345",
        )
        self.client.force_authenticate(viewer)

        list_response = self.client.get("/api/v1/onboard-spares/spares/")
        create_response = self.client.post(
            "/api/v1/onboard-spares/authorities/",
            {"name": "DEPOT"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

    def test_survey_demand_and_receive_flow_is_linked(self):
        issue = Issue.objects.create(
            spare=self.spare,
            username=self.user,
            quantity_issued=1,
        )
        survey = Survey.objects.create(
            issue_entry=issue,
            spare=self.spare,
            quantity_tosurvey=1,
            dart_number="dart-21",
            is_iif=True,
        )
        post_survey = PostSurvey.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_surveyed=1,
            survey_number="sur-001",
            has_pts=True,
            created_by="store-user",
        )
        Demand.objects.create(
            issue_entry=issue,
            spare=self.spare,
            quantity_todemand=1,
            survey_entry=post_survey,
            is_iif=True,
        )
        post_demand = PostDemand.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_demanded=1,
            demand_number="dem-001",
            created_by="store-user",
        )
        Receive.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_toreceive=1,
            demand_entry=post_demand,
        )
        PostReceive.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_received=1,
            receipt_number="rec-001",
            created_by="store-user",
        )

        self.spare.refresh_from_db()
        self.assertEqual(survey.dart_number, "DART-21")
        self.assertEqual(self.spare.quantity_available, 8)

    def test_routine_usage_records_spare_consumption_context(self):
        usage = RoutineSpareUsage.objects.create(
            routine=self.routine,
            routine_description=self.routine_description,
            spare=self.spare,
            quantity_used=2,
        )

        self.assertEqual(usage.spare, self.spare)
        self.assertEqual(usage.routine, self.routine)
        self.assertEqual(
            usage.routine_description,
            self.routine_description,
        )
        self.assertEqual(str(usage), "PN-1001 used in routine")

    def test_spares_mapping_links_equipment_class_to_ship_equipment(self):
        mapping = SparesMapping.objects.create(
            equipment_class=self.equipment_class,
            equipment=self.ship_equipment,
        )

        self.assertEqual(mapping.equipment, self.ship_equipment)
        self.assertEqual(mapping.equipment_class, self.equipment_class)

    def test_planned_routine_spare_links_to_ems_routine_plan(self):
        planned_spare = PlannedRoutineSpareList.objects.create(
            pattern_number=self.spare.pattern_number,
            planned_routine_description=self.planned_routine_description,
            quantity_required=2,
        )

        self.assertEqual(
            planned_spare.planned_routine_description,
            self.planned_routine_description,
        )

    def test_obs_api_endpoints_are_available(self):
        endpoints = [
            "/api/v1/onboard-spares/spare-classes/",
            "/api/v1/onboard-spares/equipment-classes/",
            "/api/v1/onboard-spares/denominations/",
            "/api/v1/onboard-spares/authorities/",
            "/api/v1/onboard-spares/spares/",
            "/api/v1/onboard-spares/routine-spare-usages/",
            "/api/v1/onboard-spares/issues/",
            "/api/v1/onboard-spares/issue-list/",
            "/api/v1/onboard-spares/returns/",
            "/api/v1/onboard-spares/surveys/",
            "/api/v1/onboard-spares/post-surveys/",
            "/api/v1/onboard-spares/demands/",
            "/api/v1/onboard-spares/post-demands/",
            "/api/v1/onboard-spares/receives/",
            "/api/v1/onboard-spares/post-receives/",
            "/api/v1/onboard-spares/planned-routine-spare-lists/",
            "/api/v1/onboard-spares/spares-mappings/",
            "/api/v1/onboard-spares/not-in-catted-items/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_duplicate_authority_returns_validation_error(self):
        response = self.client.post(
            "/api/v1/onboard-spares/authorities/",
            {"name": "mo"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_authority_excel_import_and_export(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["name"])
        worksheet.append(["DEPOT"])
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            "/api/v1/onboard-spares/authorities/import-excel/",
            {
                "file": SimpleUploadedFile(
                    "authorities.xlsx",
                    content.getvalue(),
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Authority.objects.filter(name="DEPOT").exists())
        export_response = self.client.get(
            "/api/v1/onboard-spares/authorities/export-excel/"
        )
        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
        self.assertIn("spreadsheetml", export_response["Content-Type"])

    def test_excel_dry_run_validates_without_saving(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["name"])
        worksheet.append(["DRY RUN AUTHORITY"])
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            "/api/v1/onboard-spares/authorities/import-excel/",
            {
                "file": SimpleUploadedFile(
                    "authority_dry_run.xlsx",
                    content.getvalue(),
                ),
                "dry_run": "true",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["valid_rows"], 1)
        self.assertFalse(Authority.objects.filter(name="DRY RUN AUTHORITY").exists())

    def test_search_filters_spares_by_inventory_details(self):
        response = self.client.get(
            "/api/v1/onboard-spares/spares/search/",
            {
                "department": self.department.pk,
                "pattern_number": "1001",
                "critical": "true",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["pattern_number"], "PN-1001")

    def test_low_stock_and_critical_lists_show_actionable_spares(self):
        low_stock_response = self.client.get("/api/v1/onboard-spares/spares/low-stock/")
        critical_response = self.client.get("/api/v1/onboard-spares/spares/critical/")

        self.assertEqual(low_stock_response.status_code, status.HTTP_200_OK)
        self.assertEqual(low_stock_response.data, [])
        self.assertEqual(critical_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            critical_response.data[0]["pattern_number"],
            "PN-1001",
        )

    def test_dashboard_returns_current_inventory_position(self):
        Issue.objects.create(
            spare=self.spare,
            username=self.user,
            quantity_issued=1,
        )

        response = self.client.get("/api/v1/onboard-spares/spares/dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_spares"], 1)
        self.assertEqual(response.data["critical_spares"], 1)
        self.assertEqual(response.data["issued_quantity"], 1)
        self.assertEqual(response.data["available_quantity"], 7)

    def test_ship_inventory_dashboard_returns_all_widget_sections(self):
        response = self.client.get("/api/v1/onboard-spares/spares/ship-dashboard/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("kpis", response.data)
        self.assertIn("availability", response.data)
        self.assertIn("supportability", response.data)
        self.assertIn("maintenance_impact", response.data)
        self.assertIn("stock_health", response.data)
        self.assertIn("decision_support", response.data)
        self.assertIn("logistics", response.data)
        self.assertIn("trend", response.data)
        self.assertIn("departments", response.data)
        self.assertEqual(response.data["availability"]["total_items"], 1)

    def test_ship_inventory_dashboard_search_returns_matching_spare(self):
        response = self.client.get(
            "/api/v1/onboard-spares/spares/ship-dashboard/",
            {"q": "fuel pump"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["search_result"]["pattern_number"],
            "PN-1001",
        )
        self.assertEqual(response.data["search_result"]["on_hand"], 8)
        self.assertEqual(response.data["search_result"]["on_order"], 0)

    def test_multi_issue_creates_demand_and_survey_by_spare_category(self):
        consumable_spare = Spares.objects.create(
            equipment_class=self.equipment_class,
            pattern_number="PN-CONSUME-1",
            description="Consumable filter",
            category=Spares.CONSUMABLE,
            denomination=self.denomination,
            quantity_authorised=6,
            quantity_available=6,
            authority=self.authority,
        )
        returnable_spare = Spares.objects.create(
            equipment_class=self.equipment_class,
            pattern_number="PN-RETURN-1",
            description="Returnable pump",
            category=Spares.RETURNABLE,
            denomination=self.denomination,
            quantity_authorised=5,
            quantity_available=5,
            authority=self.authority,
        )

        response = self.client.post(
            "/api/v1/onboard-spares/spares/multi-issue/",
            {
                "equipment": self.equipment.pk,
                "remarks": "ROUTINE",
                "items": [
                    {"spare": consumable_spare.pk, "quantity": 2},
                    {"spare": returnable_spare.pk, "quantity": 1},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["issues"]), 2)
        consumable_spare.refresh_from_db()
        returnable_spare.refresh_from_db()
        self.assertEqual(consumable_spare.quantity_available, 4)
        self.assertEqual(returnable_spare.quantity_available, 4)
        self.assertTrue(Demand.objects.filter(spare=consumable_spare).exists())
        self.assertTrue(Survey.objects.filter(spare=returnable_spare).exists())

    def test_multi_issue_rejects_batch_when_any_quantity_is_unavailable(self):
        response = self.client.post(
            "/api/v1/onboard-spares/spares/multi-issue/",
            {
                "remarks": "ROUTINE",
                "items": [{"spare": self.spare.pk, "quantity": 20}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Issue.objects.filter(spare=self.spare).exists())
        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 8)

    def test_spare_history_combines_inventory_transactions(self):
        issue = Issue.objects.create(
            spare=self.spare,
            username=self.user,
            quantity_issued=1,
        )
        Return.objects.create(
            spare_id=self.spare,
            quantity_returned=1,
        )
        Survey.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_tosurvey=1,
        )

        response = self.client.get(
            f"/api/v1/onboard-spares/spares/{self.spare.pk}/history/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["issues"]), 1)
        self.assertEqual(len(response.data["returns"]), 1)
        self.assertEqual(len(response.data["surveys"]), 1)

    def test_spare_class_and_equipment_class_lookups_are_filterable(self):
        spare_class_response = self.client.get(
            "/api/v1/onboard-spares/spare-classes/by-department/",
            {"department": self.department.pk},
        )
        equipment_class_response = self.client.get(
            "/api/v1/onboard-spares/equipment-classes/by-spare-class/",
            {"spare_class": self.spare_class.pk},
        )

        self.assertEqual(spare_class_response.status_code, status.HTTP_200_OK)
        self.assertEqual(spare_class_response.data[0]["name"], "MECHANICAL")
        self.assertEqual(
            equipment_class_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            equipment_class_response.data[0]["name"],
            "GENERATOR SPARES",
        )

    def test_requisition_can_initiate_survey_for_returnable_spare(self):
        response = self.client.post(
            f"/api/v1/onboard-spares/spares/{self.spare.pk}/initiate-survey/",
            {
                "quantity": 2,
                "equipment": self.equipment.pk,
                "dart_number": "DART-REQ-10",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        survey = Survey.objects.get(pk=response.data["survey"]["id"])
        self.assertEqual(survey.quantity_tosurvey, 2)
        self.assertEqual(survey.issue_entry.dart_number, "DART-REQ-10")
        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 6)

    def test_pending_survey_completion_creates_demand_queue(self):
        issue = Issue.objects.create(
            spare=self.spare,
            username=self.user,
            quantity_issued=2,
        )
        survey = Survey.objects.create(
            issue_entry=issue,
            spare=self.spare,
            quantity_tosurvey=2,
        )

        response = self.client.post(
            f"/api/v1/onboard-spares/surveys/{survey.pk}/complete/",
            {
                "quantity_surveyed": 2,
                "survey_number": "SUR-2026-10",
                "remarks": "Survey completed",
                "has_pts": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_survey = PostSurvey.objects.get(pk=response.data["post_survey"]["id"])
        demand = Demand.objects.get(pk=response.data["demand"]["id"])
        self.assertEqual(post_survey.survey_number, "SUR-2026-10")
        self.assertEqual(post_survey.created_by_user, self.user)
        self.assertEqual(demand.survey_entry, post_survey)
        self.assertEqual(demand.quantity_todemand, 2)

    def test_pending_demand_completion_creates_receive_queue(self):
        demand = Demand.objects.create(
            spare=self.spare,
            quantity_todemand=3,
        )

        response = self.client.post(
            f"/api/v1/onboard-spares/demands/{demand.pk}/complete/",
            {
                "quantity_demanded": 3,
                "demand_number": "DEM-2026-10",
                "remarks": "Demand forwarded",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_demand = PostDemand.objects.get(pk=response.data["post_demand"]["id"])
        receive = Receive.objects.get(pk=response.data["receive"]["id"])
        self.assertEqual(post_demand.demand_number, "DEM-2026-10")
        self.assertEqual(post_demand.created_by_user, self.user)
        self.assertEqual(receive.demand_entry, post_demand)
        self.assertEqual(receive.quantity_toreceive, 3)

    def test_pending_receive_completion_updates_stock_once(self):
        post_demand = PostDemand.objects.create(
            spare=self.spare,
            quantity_demanded=2,
            demand_number="DEM-2026-11",
        )
        receive = Receive.objects.create(
            spare=self.spare,
            quantity_toreceive=2,
            demand_entry=post_demand,
        )

        response = self.client.post(
            f"/api/v1/onboard-spares/receives/{receive.pk}/complete/",
            {
                "quantity_received": 2,
                "receipt_number": "REC-2026-11",
                "remarks": "Material received",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 10)
        post_receive = PostReceive.objects.get(receipt_number="REC-2026-11")
        self.assertEqual(post_receive.created_by_user, self.user)

    def test_pattern_verification_uses_ilms_item_master(self):
        Item.objects.create(
            item_code="ILMS-501",
            section_head="ENG",
            item_desc="Hydraulic seal",
            country_code="IN",
            item_deno="NOS",
            months_shelf_life=24,
            crp_category="C",
            ved_category="V",
            abc_category="A",
            review_sub_section_code="ENG",
        )

        response = self.client.post(
            "/api/v1/onboard-spares/spares/verify-pattern/",
            {"pattern_number": "ilms-501"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["category"], "CONSUMABLE")
        self.assertEqual(response.data["description"], "Hydraulic seal")

    def test_routine_requisition_reports_required_and_available_quantity(self):
        PlannedRoutineSpareList.objects.create(
            pattern_number=self.spare.pattern_number,
            planned_routine_description=self.planned_routine_description,
            quantity_required=3,
        )

        response = self.client.get(
            "/api/v1/onboard-spares/planned-routine-spare-lists/requisition/",
            {"planned_routine_description": (self.planned_routine_description.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["pattern_number"], "PN-1001")
        self.assertEqual(response.data[0]["quantity_required"], 3)
        self.assertEqual(response.data[0]["quantity_available"], 8)

    def test_defect_requisition_matches_dart_pattern_to_onboard_spare(self):
        dart = InitiateDart.objects.create(
            dart_number="DART-DEF-501",
            defective_discriptions="Fuel pump leakage",
        )
        DartSpare.objects.create(
            dart=dart,
            pattern=self.spare.pattern_number,
            description=self.spare.description,
            quantity=2,
        )

        response = self.client.get(
            "/api/v1/onboard-spares/spares/defect-requisition/",
            {"dart": dart.pk},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["pattern_number"], "PN-1001")
        self.assertEqual(response.data[0]["quantity_required"], 2)
        self.assertTrue(response.data[0]["available_onboard"])

    def test_routine_lookup_returns_equipment_routines_and_descriptions(self):
        routine_response = self.client.get(
            "/api/v1/onboard-spares/routine-spare-usages/routines/",
            {"equipment": self.equipment.pk},
        )
        description_response = self.client.get(
            ("/api/v1/onboard-spares/routine-spare-usages/routine-descriptions/"),
            {"routine": self.routine.pk},
        )

        self.assertEqual(routine_response.status_code, status.HTTP_200_OK)
        self.assertEqual(routine_response.data[0]["id"], self.routine.pk)
        self.assertEqual(
            description_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            description_response.data[0]["id"],
            self.routine_description.pk,
        )

    def test_return_lookups_list_commands_and_filter_ships(self):
        command_response = self.client.get("/api/v1/onboard-spares/returns/commands/")
        ship_response = self.client.get(
            "/api/v1/onboard-spares/returns/ships/",
            {"command": self.command.pk},
        )

        self.assertEqual(command_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            command_response.data[0]["command_name"],
            "Western Naval Command",
        )
        self.assertEqual(ship_response.status_code, status.HTTP_200_OK)
        self.assertEqual(ship_response.data[0]["name"], "Test Ship")

    def test_partial_processing_keeps_only_remaining_quantities_pending(self):
        issue = Issue.objects.create(
            spare=self.spare,
            username=self.user,
            quantity_issued=3,
        )
        issue_list = IssueList.objects.create(
            issue_entry=issue,
            quantity_toreturn=3,
        )
        survey = Survey.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_tosurvey=3,
        )
        survey_response = self.client.post(
            f"/api/v1/onboard-spares/surveys/{survey.pk}/complete/",
            {
                "quantity_surveyed": 1,
                "survey_number": "SUR-PART-1",
            },
            format="json",
        )
        survey.refresh_from_db()

        demand = Demand.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_todemand=3,
        )
        demand_response = self.client.post(
            f"/api/v1/onboard-spares/demands/{demand.pk}/complete/",
            {
                "quantity_demanded": 1,
                "demand_number": "DEM-PART-1",
            },
            format="json",
        )
        demand.refresh_from_db()

        receive = Receive.objects.create(
            spare=self.spare,
            issue_entry=issue,
            quantity_toreceive=2,
        )
        receive_response = self.client.post(
            f"/api/v1/onboard-spares/receives/{receive.pk}/complete/",
            {
                "quantity_received": 1,
                "receipt_number": "REC-PART-1",
            },
            format="json",
        )
        receive.refresh_from_db()
        issue_list.refresh_from_db()

        self.assertEqual(survey_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(demand_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(receive_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(survey.quantity_tosurvey, 2)
        self.assertEqual(demand.quantity_todemand, 2)
        self.assertEqual(receive.quantity_toreceive, 1)
        self.assertEqual(issue_list.quantity_toreturn, 2)

    def test_spare_template_download_contains_importable_headers(self):
        response = self.client.get("/api/v1/onboard-spares/spares/download-template/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("spreadsheetml", response["Content-Type"])
        self.assertIn(
            "spares_template.xlsx",
            response["Content-Disposition"],
        )

    def test_iif_item_can_be_listed_and_marked_as_incatted(self):
        item = NotInCattedItem.objects.create(spare_id=self.spare)

        pending_response = self.client.get(
            "/api/v1/onboard-spares/not-in-catted-items/pending/"
        )
        update_response = self.client.post(
            (f"/api/v1/onboard-spares/not-in-catted-items/{item.pk}/mark-incatted/")
        )

        self.assertEqual(pending_response.status_code, status.HTTP_200_OK)
        self.assertEqual(pending_response.data[0]["id"], item.pk)
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.incatted_status)
        self.assertTrue(item.is_deleted)

    def test_opdem_survey_creates_a_typed_pending_demand(self):
        survey = Survey.objects.create(
            spare=self.spare,
            quantity_tosurvey=2,
        )

        response = self.client.post(
            f"/api/v1/onboard-spares/surveys/{survey.pk}/complete/",
            {
                "quantity_surveyed": 2,
                "survey_type": "OPDEM",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_survey = PostSurvey.objects.get(pk=response.data["post_survey"]["id"])
        self.assertEqual(post_survey.survey_type, PostSurvey.OPDEM)
        self.assertEqual(post_survey.survey_number, "OPDEM")
        self.assertTrue(Demand.objects.filter(survey_entry=post_survey).exists())

    def test_pattern_verification_falls_back_to_wlms_and_checks_category(self):
        wlms_equipment = WLMSEquipment.objects.create(eqpt_name="WED Pump")
        WLMSSpare.objects.create(
            item_code="WLMS-501",
            item_desc="WED pump cartridge",
            category="R",
            eqpt=wlms_equipment,
            denom_id="NOS",
        )

        response = self.client.post(
            "/api/v1/onboard-spares/spares/verify-pattern/",
            {
                "pattern_number": "wlms-501",
                "category": Spares.CONSUMABLE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], "WLMS")
        self.assertFalse(response.data["valid"])
        self.assertTrue(response.data["category_mismatch"])
        self.assertEqual(response.data["category"], Spares.RETURNABLE)

    def test_update_pattern_marks_pending_iif_item_resolved(self):
        pending_item = NotInCattedItem.objects.create(spare_id=self.spare)

        response = self.client.post(
            "/api/v1/onboard-spares/spares/update-pattern/",
            {
                "spare_pk": self.spare.pk,
                "pattern_number": "fixed-9001",
                "category": Spares.PERMANENT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.spare.refresh_from_db()
        pending_item.refresh_from_db()
        self.assertEqual(self.spare.pattern_number, "FIXED-9001")
        self.assertTrue(pending_item.incatted_status)
        self.assertTrue(pending_item.is_deleted)

    def test_spare_detail_summary_returns_flat_reference_shape(self):
        response = self.client.get(
            f"/api/v1/onboard-spares/spares/{self.spare.pk}/detail-summary/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["department"], "Engineering")
        self.assertEqual(response.data["data"]["spare_class"], "MECHANICAL")
        self.assertEqual(response.data["data"]["images"], ["/media/default.png"])

    def test_defect_multi_issue_updates_dart_spare_quantity(self):
        dart = InitiateDart.objects.create(
            dart_number="DART-DEF-900",
            defective_discriptions="Fuel pump leakage",
        )
        dart_spare = DartSpare.objects.create(
            dart=dart,
            pattern=self.spare.pattern_number,
            description=self.spare.description,
            quantity=3,
        )

        response = self.client.post(
            "/api/v1/onboard-spares/spares/defect-multi-issue/",
            {
                "remarks": "defect",
                "dart_number": dart.dart_number,
                "equipment": self.equipment.pk,
                "items": [
                    {
                        "pattern_number": self.spare.pattern_number,
                        "quantity_issued": 2,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.spare.refresh_from_db()
        dart_spare.refresh_from_db()
        self.assertEqual(self.spare.quantity_available, 6)
        self.assertEqual(dart_spare.quantity, 1)
        self.assertTrue(Survey.objects.filter(spare=self.spare).exists())

    def test_cart_actions_soft_delete_routine_and_delete_defect_spares(self):
        planned_spare = PlannedRoutineSpareList.objects.create(
            pattern_number=self.spare.pattern_number,
            planned_routine_description=self.planned_routine_description,
            quantity_required=1,
        )
        routine_response = self.client.post(
            (
                "/api/v1/onboard-spares/planned-routine-spare-lists/"
                "soft-delete-after-cart/"
            ),
            {"pk": self.spare.pk, "inventory_type": "OBS"},
            format="json",
        )
        planned_spare.refresh_from_db()

        dart = InitiateDart.objects.create(dart_number="DART-DEL-1")
        dart_spare = DartSpare.objects.create(
            dart=dart,
            pattern=self.spare.pattern_number,
            description=self.spare.description,
            quantity=1,
        )
        defect_response = self.client.post(
            (
                "/api/v1/onboard-spares/planned-routine-spare-lists/"
                "delete-defect-requisition-spare/"
            ),
            {"pk": dart_spare.pk, "inventory_type": "OBS"},
            format="json",
        )

        self.assertEqual(routine_response.status_code, status.HTTP_200_OK)
        self.assertTrue(planned_spare.is_deleted)
        self.assertEqual(defect_response.status_code, status.HTTP_200_OK)
        self.assertFalse(DartSpare.objects.filter(pk=dart_spare.pk).exists())

    def test_wed_mapping_check_reports_unmapped_and_mapped_spares(self):
        wlms_equipment = WLMSEquipment.objects.create(eqpt_name="WED Pump")
        wlms_spare = WLMSSpare.objects.create(
            item_code="WED-777",
            item_desc="WED pump gasket",
            category="P",
            eqpt=wlms_equipment,
        )
        planned_description = PlannedSparesDescription.objects.create(
            wlms_spare_id=wlms_spare,
            spares_required=True,
        )
        planned_wed_spare = PlannedWEDSpareList.objects.create(
            pattern_number=wlms_spare.item_code,
            planned_spares_description=planned_description,
            quantity_required=1,
        )

        unmapped_response = self.client.post(
            "/api/v1/onboard-spares/spares/check-wed-mapping/",
            {"pks": [planned_wed_spare.pk]},
            format="json",
        )
        SpareDataMap.objects.create(
            equipment=self.ship_equipment,
            wed_equipment=wlms_equipment,
        )
        mapped_response = self.client.post(
            "/api/v1/onboard-spares/spares/check-wed-mapping/",
            {"pks": str(planned_wed_spare.pk)},
            format="json",
        )

        self.assertEqual(unmapped_response.status_code, status.HTTP_200_OK)
        self.assertFalse(unmapped_response.data["all_mapped"])
        self.assertEqual(
            unmapped_response.data["unmapped"][0]["pattern_number"], "WED-777"
        )
        self.assertEqual(mapped_response.status_code, status.HTTP_200_OK)
        self.assertTrue(mapped_response.data["all_mapped"])
