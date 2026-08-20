from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient

from dart.models import InitiateDart
from ems.models import (
    AddRoutineDetails,
    EquipmentName,
    RoutineDescription,
    UniqueRoutineName,
)
from sfd.models import ShipEquipment

from .models import (
    WEDIIF,
    WEDIIFDetails,
    DartWedSpare,
    DemandDetails,
    PlannedSparesDescription,
    PlannedWEDSpareList,
    PTSDemandDetails,
    ReceiveDemandDetails,
    SignalDemand,
    SpareDataMap,
    SurveyFormsDetails,
    SurveyFormsItems,
    SurveyReceiptsDetails,
    WLMSEquipment,
    WLMSSpare,
)


class WLMSApiFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="wlms-manager",
            password="Pass@12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.equipment = WLMSEquipment.objects.create(
            eqpt_id=501,
            eqpt_name="MISSILE LAUNCHER",
            remarks="WED controlled equipment",
            is_active=True,
            control_cell_id=11,
            sco_id=21,
            depot_id=31,
        )
        self.spare = WLMSSpare.objects.create(
            wlms_inventory="WED-INV-001",
            item_code="WLMS-1001",
            item_desc="LAUNCHER INTERFACE MODULE",
            category="REPAIRABLE",
            eqpt=self.equipment,
            denom_id="NOS",
            sh_name="WED",
            latest_qty=3,
            is_active=True,
            typeofspare="WEAPON SUPPORT",
        )
        self.ship_equipment = ShipEquipment.objects.create(
            nomenclature="Missile Launcher",
            equipment_serial_no="WED-7001",
        )
        self.ems_equipment = EquipmentName.objects.create(
            name="Missile Launcher",
            equipment_code="WED-EMS-01",
        )
        self.routine_name = UniqueRoutineName.objects.create(
            name="Launcher Quarterly Routine",
        )
        self.routine = AddRoutineDetails.objects.create(
            equipment_name=self.ems_equipment,
            routine_name=self.routine_name,
            routine_no="WED-RT-01",
        )
        self.routine_description = RoutineDescription.objects.create(
            equipment_name=self.ems_equipment,
            routine_name=self.routine_name,
            add_routine_details=self.routine,
            routine_no="WED-RT-01",
            routine_description="Inspect launcher support interfaces.",
            by_whom="Weapon Engineering Department",
        )
        self.dart = InitiateDart.objects.create(
            dart_number="D-WED-801",
            equipment_ship=self.ship_equipment,
        )

    def test_create_wed_equipment(self):
        payload = {
            "eqpt_id": 502,
            "eqpt_name": "FIRE CONTROL RADAR",
            "remarks": "Weapon support equipment",
            "is_active": True,
            "control_cell_id": 12,
            "sco_id": 22,
            "depot_id": 32,
        }

        response = self.client.post(
            "/api/v1/wlms/equipment/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(WLMSEquipment.objects.filter(eqpt_id=502).exists())

    def test_create_wed_spare(self):
        payload = {
            "wlms_inventory": "WED-INV-002",
            "item_code": "WLMS-1002",
            "item_desc": "RADAR COOLING FAN",
            "category": "CONSUMABLE",
            "eqpt": self.equipment.id,
            "denom_id": "NOS",
            "sh_name": "WED",
            "latest_qty": 8,
            "is_active": True,
            "typeofspare": "WEAPON SUPPORT",
        }

        response = self.client.post("/api/v1/wlms/spares/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        spare = WLMSSpare.objects.get(item_code="WLMS-1002")
        self.assertEqual(spare.eqpt_id, self.equipment.id)
        self.assertEqual(spare.denom_id, "NOS")
        self.assertEqual(spare.latest_qty, 8)

    def test_filter_spares_by_equipment(self):
        other_equipment = WLMSEquipment.objects.create(
            eqpt_id=601,
            eqpt_name="TORPEDO TUBE",
            is_active=True,
        )
        WLMSSpare.objects.create(
            item_code="WLMS-2001",
            item_desc="TORPEDO TUBE SEAL",
            eqpt=other_equipment,
            latest_qty=2,
        )

        response = self.client.get(
            f"/api/v1/wlms/spares/?equipment_id={self.equipment.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["item_code"], "WLMS-1001")

    def test_create_spare_data_mapping(self):
        payload = {
            "equipment": self.ship_equipment.pk,
            "wed_equipment": self.equipment.id,
        }

        response = self.client.post(
            "/api/v1/wlms/spare-data-maps/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        mapping = SpareDataMap.objects.get(id=response.data["id"])
        self.assertEqual(mapping.equipment, self.ship_equipment)
        self.assertEqual(mapping.wed_equipment_id, self.equipment.id)

    def test_create_planned_wed_spare(self):
        description_payload = {
            "wlms_spare_id": self.spare.id,
            "routine_description_id": self.routine_description.pk,
            "spares_required": True,
            "is_deleted": False,
        }

        description_response = self.client.post(
            "/api/v1/wlms/planned-descriptions/",
            description_payload,
            format="json",
        )
        self.assertEqual(description_response.status_code, 201)

        list_payload = {
            "pattern_number": "WED-PN-1001",
            "planned_spares_description": description_response.data["id"],
            "quantity_required": 2,
            "is_deleted": False,
        }

        list_response = self.client.post(
            "/api/v1/wlms/planned-spares/",
            list_payload,
            format="json",
        )

        self.assertEqual(list_response.status_code, 201)
        planned_list = PlannedWEDSpareList.objects.get(id=list_response.data["id"])
        self.assertEqual(
            planned_list.planned_spares_description_id,
            description_response.data["id"],
        )
        self.assertEqual(planned_list.pattern_number, "WED-PN-1001")

    def test_reject_invalid_dart_wed_ids(self):
        payload = {
            "equipment_id": 1000000,
            "wed_spare": self.spare.id,
            "dart_id": 1000000,
            "pattern": "DART-WED-001",
            "description": "DART linked WED spare",
            "quantity": 1,
            "is_delete": False,
        }

        response = self.client.post(
            "/api/v1/wlms/dart-wed-spares/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("equipment_id", response.data)
        self.assertIn("dart_id", response.data)

    def test_create_survey_to_receive_flow(self):
        planned_description = PlannedSparesDescription.objects.create(
            wlms_spare_id=self.spare,
            routine_description_id=self.routine_description,
            spares_required=True,
        )
        dart_spare = DartWedSpare.objects.create(
            equipment_id=self.ship_equipment,
            wed_spare=self.spare,
            dart_id=self.dart,
            pattern="DART-WED-002",
            description="DART spare for survey and demand",
            quantity=1,
        )

        survey_receipt_response = self.client.post(
            "/api/v1/wlms/survey-receipts/",
            {
                "wed_spares_id": self.spare.id,
                "spare_cart_name": "WED SURVEY CART",
                "wed_routine_plan": planned_description.id,
                "wed_dart": dart_spare.id,
                "is_save": True,
                "is_survey": True,
                "is_sync": False,
                "is_hod": False,
                "is_approval": False,
                "wlms_status": "survey created",
            },
            format="json",
        )
        self.assertEqual(survey_receipt_response.status_code, 201)

        survey_form_response = self.client.post(
            "/api/v1/wlms/survey-forms/",
            {
                "survey_rec_id": survey_receipt_response.data["id"],
                "rece_qty": "1",
                "held_certificate_type": "OEM",
                "held_certificate_no": "CERT-001",
                "survey_no": "SUR-WED-001",
                "wlms_survey_no": "WLMS-SUR-001",
                "ss_remarks": "accepted for survey",
                "scrap_qty": "0",
            },
            format="json",
        )
        self.assertEqual(survey_form_response.status_code, 201)

        survey_item_response = self.client.post(
            "/api/v1/wlms/survey-items/",
            {
                "survey_details_id": survey_form_response.data["id"],
                "wed_spares_id": self.spare.id,
                "item_serial_no": "SER-WED-001",
            },
            format="json",
        )
        self.assertEqual(survey_item_response.status_code, 201)

        pts_response = self.client.post(
            "/api/v1/wlms/pts-demands/",
            {
                "wed_spares_id": self.spare.id,
                "wed_routine_plan": planned_description.id,
                "wed_dart": dart_spare.id,
                "survey_no": "SUR-WED-001",
                "PTS_demand_no": "PTS-WED-001",
                "demand_no": "DEM-WED-001",
                "demand_qty": "1",
                "remarks": "PTS raised after survey",
                "is_save": True,
                "is_pts": True,
                "is_sync": False,
                "is_rejected": False,
                "spare_cart_name": "WED PTS CART",
                "is_hod": False,
                "is_approval": False,
            },
            format="json",
        )
        self.assertEqual(pts_response.status_code, 201)

        demand_response = self.client.post(
            "/api/v1/wlms/demands/",
            {
                "wed_spares_id": self.spare.id,
                "wed_routine_plan": planned_description.id,
                "wed_dart": dart_spare.id,
                "survey_no": "SUR-WED-001",
                "PTS_no": "PTS-WED-001",
                "demand_no": "DEM-WED-001",
                "demand_qty": "1",
                "remarks": "demand raised to WED",
                "is_save": True,
                "is_demand": True,
                "is_sync": False,
                "is_rejected": False,
                "spare_cart_name": "WED DEMAND CART",
                "is_hod": False,
                "is_approval": False,
                "is_delete": False,
            },
            format="json",
        )
        self.assertEqual(demand_response.status_code, 201)

        receive_response = self.client.post(
            "/api/v1/wlms/receive-demands/",
            {
                "demand_details": demand_response.data["id"],
                "demand_number": "DEM-WED-001",
                "demand_date": "2026-06-03",
                "demand_quantity": 1,
                "demand_status": "received",
                "swmm_demandno": "SWMM-WED-001",
                "dart_no": "DART-801",
                "gate_pass_no": "GP-WED-001",
                "gate_pass_date": "2026-06-03T10:00:00Z",
            },
            format="json",
        )

        self.assertEqual(receive_response.status_code, 201)
        self.assertTrue(
            SurveyReceiptsDetails.objects.filter(wed_spares_id=self.spare).exists()
        )
        self.assertTrue(
            SurveyFormsDetails.objects.filter(
                survey_rec_id_id=survey_receipt_response.data["id"]
            ).exists()
        )
        self.assertTrue(
            SurveyFormsItems.objects.filter(wed_spares_id=self.spare).exists()
        )
        self.assertTrue(
            PTSDemandDetails.objects.filter(PTS_demand_no="PTS-WED-001").exists()
        )
        demand = DemandDetails.objects.get(id=demand_response.data["id"])
        receive = ReceiveDemandDetails.objects.get(id=receive_response.data["id"])
        self.assertEqual(demand.wed_spares_id_id, self.spare.id)
        self.assertEqual(receive.demand_details_id, demand.id)
        self.assertEqual(receive.demand_status, "received")

    def test_reject_invalid_receive_quantity(self):
        response = self.client.post(
            "/api/v1/wlms/receive-demands/",
            {
                "demand_number": "DEM-WED-002",
                "demand_quantity": 1000000,
                "demand_status": "received",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("demand_quantity", response.data)

    def test_wlms_routes_are_available(self):
        paths = [
            "/api/v1/wlms/equipment/",
            "/api/v1/wlms/spares/",
            "/api/v1/wlms/spare-data-maps/",
            "/api/v1/wlms/planned-descriptions/",
            "/api/v1/wlms/planned-spares/",
            "/api/v1/wlms/dart-wed-spares/",
            "/api/v1/wlms/survey-receipts/",
            "/api/v1/wlms/survey-forms/",
            "/api/v1/wlms/survey-items/",
            "/api/v1/wlms/pts-demands/",
            "/api/v1/wlms/demands/",
            "/api/v1/wlms/receive-demands/",
            "/api/v1/wlms/wediif/",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(resolve(path))

    def test_equipment_excel_import_and_export(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["eqpt_id", "eqpt_name", "remarks", "is_active"])
        worksheet.append([777, "TORPEDO LAUNCHER", "Imported from Excel", True])
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            "/api/v1/wlms/equipment/import-excel/",
            {
                "file": SimpleUploadedFile(
                    "wlms_equipment.xlsx",
                    content.getvalue(),
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(WLMSEquipment.objects.filter(eqpt_id=777).exists())
        export_response = self.client.get("/api/v1/wlms/equipment/export-excel/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("spreadsheetml", export_response["Content-Type"])

    def test_dashboard_and_search_show_active_wed_inventory(self):
        WLMSSpare.objects.create(
            item_code="WLMS-INACTIVE",
            item_desc="Inactive radar module",
            latest_qty=0,
            is_active=False,
        )

        search_response = self.client.get(
            "/api/v1/wlms/spares/",
            {"q": "launcher", "active": "true"},
        )
        dashboard_response = self.client.get("/api/v1/wlms/spares/dashboard/")

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(len(search_response.data), 1)
        self.assertEqual(search_response.data[0]["item_code"], "WLMS-1001")
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(dashboard_response.data["active_spares"], 1)
        self.assertEqual(dashboard_response.data["available_quantity"], 3)

    def test_planned_spare_can_be_added_to_demand_cart(self):
        description = PlannedSparesDescription.objects.create(
            wlms_spare_id=self.spare,
            routine_description_id=self.routine_description,
            spares_required=True,
        )
        planned_spare = PlannedWEDSpareList.objects.create(
            pattern_number=self.spare.item_code,
            planned_spares_description=description,
            quantity_required=2,
        )

        first_response = self.client.post(
            "/api/v1/wlms/demands/add-to-cart/",
            {"source": "planned", "source_ids": [planned_spare.pk]},
            format="json",
        )
        second_response = self.client.post(
            "/api/v1/wlms/demands/add-to-cart/",
            {"source": "planned", "source_ids": [planned_spare.pk]},
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        demand = DemandDetails.objects.get(wed_spares_id=self.spare)
        self.assertEqual(demand.demand_qty, "2")
        self.assertEqual(demand.wed_routine_plan, description)

    def test_demand_approval_generates_reference_and_lists_outbox(self):
        demand = DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_qty="1",
            spare_cart_name="Demand",
        )

        send_response = self.client.post(
            f"/api/v1/wlms/demands/{demand.pk}/send-for-approval/"
        )
        approve_response = self.client.post(
            f"/api/v1/wlms/demands/{demand.pk}/approve/"
        )
        number_response = self.client.post(
            f"/api/v1/wlms/demands/{demand.pk}/generate-number/"
        )
        outbox_response = self.client.get("/api/v1/wlms/demands/outbox/")

        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(approve_response.status_code, 200)
        self.assertEqual(number_response.status_code, 200)
        self.assertEqual(
            number_response.data["demand_no"],
            f"SWMM/DEMAND/{timezone.now().year}/{demand.pk:03d}",
        )
        self.assertEqual(outbox_response.status_code, 200)
        self.assertEqual(outbox_response.data[0]["id"], demand.pk)

    def test_receive_demand_updates_wed_stock_once(self):
        demand = DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_no="SWMM/DEMAND/2026/001",
            demand_qty="2",
            is_demand=True,
            is_approval=True,
        )

        first_response = self.client.post(
            "/api/v1/wlms/receive-demands/",
            {
                "demand_details": demand.pk,
                "demand_number": demand.demand_no,
                "demand_quantity": 2,
                "demand_status": "received",
            },
            format="json",
        )
        second_response = self.client.post(
            "/api/v1/wlms/receive-demands/",
            {
                "demand_details": demand.pk,
                "demand_number": demand.demand_no,
                "demand_quantity": 2,
                "demand_status": "received",
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 400)
        self.spare.refresh_from_db()
        self.assertEqual(self.spare.latest_qty, 5)

    def test_item_context_returns_mapping_and_workflow_history(self):
        SpareDataMap.objects.create(
            equipment=self.ship_equipment,
            wed_equipment=self.equipment,
        )
        DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_no="SWMM/DEMAND/2026/002",
        )
        SurveyReceiptsDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            spare_cart_name="Survey",
        )

        response = self.client.get(f"/api/v1/wlms/spares/{self.spare.pk}/context/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["spare"]["item_code"], "WLMS-1001")
        self.assertEqual(len(response.data["equipment_mappings"]), 1)
        self.assertEqual(len(response.data["demands"]), 1)
        self.assertEqual(len(response.data["surveys"]), 1)

    def test_routine_lookup_returns_planned_wed_spares(self):
        description = PlannedSparesDescription.objects.create(
            wlms_spare_id=self.spare,
            routine_description_id=self.routine_description,
            spares_required=True,
        )
        PlannedWEDSpareList.objects.create(
            pattern_number=self.spare.item_code,
            planned_spares_description=description,
            quantity_required=3,
        )

        response = self.client.get(
            "/api/v1/wlms/planned-spares/by-routine/",
            {"routine_description": self.routine_description.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["pattern_number"], "WLMS-1001")
        self.assertEqual(response.data[0]["quantity_required"], 3)

    def test_obs_spare_can_be_added_to_wed_iif_without_duplicates(self):
        from obs.models import (
            Authority,
            EquipmentClass,
            SpareClass,
            Spares,
        )

        spare_class = SpareClass.objects.create(name="WED IIF CLASS")
        equipment_class = EquipmentClass.objects.create(
            name="WED IIF EQUIPMENT",
            spare_class=spare_class,
        )
        authority = Authority.objects.create(name="WED")
        obs_spare = Spares.objects.create(
            equipment_class=equipment_class,
            pattern_number="OBS-WED-IIF-1",
            description="Weapon support item awaiting incat",
            quantity_authorised=1,
            quantity_available=1,
            authority=authority,
        )

        first_response = self.client.post(
            "/api/v1/wlms/wediif/add-items/",
            {"spare_ids": [obs_spare.pk]},
            format="json",
        )
        second_response = self.client.post(
            "/api/v1/wlms/wediif/add-items/",
            {"spare_ids": [obs_spare.pk]},
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(WEDIIF.objects.filter(spare_id=obs_spare).count(), 1)

    def test_approved_survey_form_gets_a_unique_survey_number(self):
        survey = SurveyReceiptsDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            spare_cart_name="Survey",
            is_hod=True,
            is_approval=True,
        )
        form = SurveyFormsDetails.objects.create(
            survey_rec_id=survey,
            rece_qty="1",
            scrap_qty="1",
        )

        response = self.client.post(
            f"/api/v1/wlms/survey-forms/{form.pk}/generate-number/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["survey_no"],
            f"SWMM/SURVEY/{timezone.now().year}/{form.pk:03d}",
        )
        survey.refresh_from_db()
        self.assertTrue(survey.is_survey)

    def test_approved_pts_gets_a_unique_reference_number(self):
        pts = PTSDemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_qty="1",
            spare_cart_name="PTS",
            is_hod=True,
            is_approval=True,
        )

        response = self.client.post(
            f"/api/v1/wlms/pts-demands/{pts.pk}/generate-number/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["PTS_demand_no"],
            f"SWMM/PTS/{timezone.now().year}/{pts.pk:03d}",
        )
        pts.refresh_from_db()
        self.assertTrue(pts.is_pts)

    def test_completed_demand_can_be_marked_synced(self):
        demand = DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_no="SWMM/DEMAND/2026/003",
            demand_qty="1",
            is_demand=True,
            is_hod=True,
            is_approval=True,
        )

        response = self.client.post(f"/api/v1/wlms/demands/{demand.pk}/mark-synced/")

        self.assertEqual(response.status_code, 200)
        demand.refresh_from_db()
        self.assertTrue(demand.is_sync)
        self.assertIsNotNone(demand.sync_date)

    def test_receive_queue_excludes_demands_already_received(self):
        pending = DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_no="SWMM/DEMAND/2026/004",
            demand_qty="1",
            is_demand=True,
        )
        received = DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_no="SWMM/DEMAND/2026/005",
            demand_qty="1",
            is_demand=True,
        )
        ReceiveDemandDetails.objects.create(
            demand_details=received,
            demand_number=received.demand_no,
            demand_quantity=1,
            demand_status="received",
        )

        response = self.client.get("/api/v1/wlms/demands/receive-queue/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], pending.pk)

    def test_demand_consolidation_groups_pending_wed_spares(self):
        DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_qty="2",
        )
        DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_qty="3",
        )

        response = self.client.get("/api/v1/wlms/demands/consolidation/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["item_code"], "WLMS-1001")
        self.assertEqual(response.data[0]["record_count"], 2)
        self.assertEqual(response.data[0]["total_quantity"], 5)

    def test_routine_context_reports_equipment_mapping(self):
        mapping = SpareDataMap.objects.create(
            equipment=self.ship_equipment,
            wed_equipment=self.equipment,
        )
        description = PlannedSparesDescription.objects.create(
            wlms_spare_id=self.spare,
            routine_description_id=self.routine_description,
            spares_required=True,
        )

        response = self.client.get(
            f"/api/v1/wlms/spares/{self.spare.pk}/routine-context/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["mapped"])
        self.assertEqual(
            response.data["ship_equipment_id"],
            mapping.equipment_id,
        )
        self.assertEqual(
            response.data["routine_description_id"],
            description.routine_description_id_id,
        )

    def test_opdem_requires_requesting_ship_and_inventory_item(self):
        response = self.client.post(
            "/api/v1/wlms/signal-demands/",
            {
                "demand_type": "OPDEM",
                "demand_number": "OPDEM-2026-001",
                "dtg": timezone.now().isoformat(),
                "demand_quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("requesting_ship", response.data)
        self.assertIn("inventory_item", response.data)

    def test_storedem_can_be_registered_and_forwarded(self):
        from master.models import MShipCommand, Ship, UnitType

        command = MShipCommand.objects.create(
            command_id=901,
            command_code="ENC",
            command_name="Eastern Naval Command",
            active=True,
        )
        unit_type = UnitType.objects.create(id=901, name="WED test unit")
        ship = Ship.objects.create(
            code="SHIP-WED-01",
            name="WED Test Ship",
            command=command,
            unit_type=unit_type,
        )
        create_response = self.client.post(
            "/api/v1/wlms/signal-demands/",
            {
                "demand_type": "STOREDEM",
                "demand_number": "STOREDEM-2026-001",
                "dtg": timezone.now().isoformat(),
                "requesting_ship": ship.pk,
                "equipment": self.equipment.pk,
                "wed_spare": self.spare.pk,
                "demand_quantity": 2,
                "remarks": "Routine store replenishment",
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        demand_id = create_response.data["id"]
        forward_response = self.client.post(
            f"/api/v1/wlms/signal-demands/{demand_id}/forward/"
        )

        self.assertEqual(forward_response.status_code, 200)
        demand = SignalDemand.objects.get(pk=demand_id)
        self.assertEqual(demand.status, SignalDemand.FORWARDED)

    def test_candem_requires_a_different_receiver_ship(self):
        from master.models import MShipCommand, Ship, UnitType

        command = MShipCommand.objects.create(
            command_id=902,
            command_code="SNC",
            command_name="Southern Naval Command",
            active=True,
        )
        unit_type = UnitType.objects.create(id=902, name="Donor unit")
        ship = Ship.objects.create(
            code="SHIP-WED-02",
            name="Donor Ship",
            command=command,
            unit_type=unit_type,
        )

        response = self.client.post(
            "/api/v1/wlms/signal-demands/",
            {
                "demand_type": "CANDEM",
                "demand_number": "CANDEM-2026-001",
                "dtg": timezone.now().isoformat(),
                "requesting_ship": ship.pk,
                "receiver_ship": ship.pk,
                "wed_spare": self.spare.pk,
                "demand_quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("receiver_ship", response.data)

    def test_signal_demand_list_can_be_filtered_by_workflow_type(self):
        from master.models import MShipCommand, Ship, UnitType

        command = MShipCommand.objects.create(
            command_id=903,
            command_code="WNC",
            command_name="Western Naval Command",
            active=True,
        )
        unit_type = UnitType.objects.create(id=903, name="Signal demand unit")
        ship = Ship.objects.create(
            code="SHIP-WED-03",
            name="Signal Demand Ship",
            command=command,
            unit_type=unit_type,
        )
        for demand_type in (SignalDemand.OPDEM, SignalDemand.STOREDEM):
            SignalDemand.objects.create(
                demand_type=demand_type,
                demand_number=f"{demand_type}-2026-010",
                dtg=timezone.now(),
                requesting_ship=ship,
                wed_spare=self.spare,
                demand_quantity=1,
                created_by=self.user,
            )

        response = self.client.get(
            "/api/v1/wlms/signal-demands/",
            {"demand_type": SignalDemand.OPDEM},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["demand_type"], SignalDemand.OPDEM)

    def test_wed_mapping_can_store_specific_spare_link(self):
        response = self.client.post(
            "/api/v1/wlms/spare-data-maps/",
            {
                "equipment": self.ship_equipment.pk,
                "wed_equipment": self.equipment.pk,
                "wed_spares": self.spare.pk,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        mapping = SpareDataMap.objects.get(pk=response.data["id"])
        self.assertEqual(mapping.wed_spares, self.spare)

    def test_wlms_bulk_hod_actions_update_reference_status_fields(self):
        demand = DemandDetails.objects.create(
            user_id=self.user,
            wed_spares_id=self.spare,
            demand_qty="2",
        )

        send_response = self.client.post(
            "/api/v1/wlms/demands/bulk-send-for-approval/",
            {"ids": [demand.pk]},
            format="json",
        )
        approve_response = self.client.post(
            "/api/v1/wlms/demands/bulk-approve/",
            {"ids": [demand.pk]},
            format="json",
        )

        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(approve_response.status_code, 200)
        demand.refresh_from_db()
        self.assertTrue(demand.is_hod)
        self.assertTrue(demand.is_approval)
        self.assertEqual(demand.wlms_demand_status, "Approved")

    def test_wlms_iif_detail_and_approval_flow(self):
        from obs.models import Authority, Denomination as ObsDenomination
        from obs.models import EquipmentClass, SpareClass, Spares
        from master.models import Department

        department = Department.objects.create(name="WED", code="WED")
        spare_class = SpareClass.objects.create(name="WED CLASS", department=department)
        equipment_class = EquipmentClass.objects.create(
            name="WED EQPT",
            spare_class=spare_class,
        )
        denomination = ObsDenomination.objects.create(name="NOS", department=department)
        authority = Authority.objects.create(name="WED")
        obs_spare = Spares.objects.create(
            equipment_class=equipment_class,
            pattern_number="OBS-WED-1",
            description="WED onboard spare",
            category=Spares.PERMANENT,
            denomination=denomination,
            quantity_authorised=2,
            quantity_available=1,
            authority=authority,
        )
        add_response = self.client.post(
            "/api/v1/wlms/wediif/add-items/",
            {"spare_ids": [obs_spare.pk]},
            format="json",
        )
        iif_id = add_response.data["created"][0]["id"]
        detail_response = self.client.post(
            "/api/v1/wlms/wediif-details/",
            {"wed_iif": iif_id, "iif_no": "WED-IIF-001"},
            format="json",
        )
        send_response = self.client.post(
            f"/api/v1/wlms/wediif/{iif_id}/send-for-approval/"
        )
        approve_response = self.client.post(f"/api/v1/wlms/wediif/{iif_id}/approve/")

        self.assertEqual(add_response.status_code, 201)
        self.assertEqual(detail_response.status_code, 201)
        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(approve_response.status_code, 200)
        iif = WEDIIF.objects.get(pk=iif_id)
        self.assertEqual(iif.user_id, self.user)
        self.assertTrue(iif.is_hod)
        self.assertTrue(iif.is_approval)
        self.assertTrue(WEDIIFDetails.objects.filter(wed_iif=iif).exists())

    def test_wlms_search_helper_aliases_return_expected_data(self):
        equipment_response = self.client.get(
            "/api/v1/wlms/spares/equipment-list/",
            {"active": "true"},
        )
        spares_response = self.client.get(
            "/api/v1/wlms/spares/by-equipment/",
            {"equipment_id": self.equipment.pk},
        )
        SpareDataMap.objects.create(
            equipment=self.ship_equipment,
            wed_equipment=self.equipment,
            wed_spares=self.spare,
        )
        mapping_response = self.client.get(
            "/api/v1/wlms/spare-data-maps/sfd-equipment-for-wed/",
            {"wed_equipment": self.equipment.pk},
        )

        self.assertEqual(equipment_response.status_code, 200)
        self.assertEqual(spares_response.status_code, 200)
        self.assertEqual(mapping_response.status_code, 200)
        self.assertEqual(equipment_response.data[0]["id"], self.equipment.pk)
        self.assertEqual(spares_response.data[0]["id"], self.spare.pk)
        self.assertEqual(mapping_response.data[0]["wed_spares"], self.spare.pk)
