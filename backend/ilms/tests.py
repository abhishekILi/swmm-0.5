from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve
from openpyxl import Workbook
from rest_framework.test import APIClient

from dart.models import InitiateDart
from ems.models import (
    AddRoutineDetails,
    EquipmentName,
    RoutineDescription,
    UniqueRoutineName,
)
from sfd.models import Equipment, ShipEquipment

from .models import (
    IIF,
    Customer,
    CustomerEquipment,
    CustomerEquipmentLine,
    DartMOSpare,
    DemandDetails,
    Item,
    MoMappingTable,
    MOPlannedSparesDescription,
    PlannedMOSpareList,
    PTSDetails,
    SurveyDetails,
    Vendor,
)


class ILMSApiFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="ilms-manager",
            password="Pass@12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)
        self.item = Item.objects.create(
            item_code="ILMS-1001",
            section_head="ENGINEERING",
            item_desc="HYDRAULIC FILTER ELEMENT",
            country_code="IN",
            item_deno="NOS",
            months_shelf_life=24,
            crp_category="C",
            ved_category="V",
            abc_category="A",
            review_sub_section_code="ENG",
            incat_yn=True,
        )
        self.vendor = Vendor.objects.create(
            vendor_code="VEN-001",
            name="NAVAL SPARES SUPPLIER",
            vendor_class="OEM",
            country_code="IN",
        )
        self.ship_equipment = ShipEquipment.objects.create(
            nomenclature="Hydraulic System",
            equipment_serial_no="ILMS-501",
        )
        self.equipment = Equipment.objects.create(
            equipment_code="ILMS-EQ-501",
            ilms_eq_code="ILMS-501",
        )
        self.dart = InitiateDart.objects.create(
            equipment_ship=self.ship_equipment,
            dart_number="D-ILMS-001",
        )
        self.ems_equipment = EquipmentName.objects.create(
            name="Hydraulic System",
            equipment_code="ILMS-EMS-01",
        )
        self.routine_name = UniqueRoutineName.objects.create(
            name="Hydraulic System Quarterly Routine",
        )
        self.routine = AddRoutineDetails.objects.create(
            equipment_name=self.ems_equipment,
            routine_name=self.routine_name,
            routine_no="ILMS-RT-01",
        )
        self.routine_description = RoutineDescription.objects.create(
            equipment_name=self.ems_equipment,
            routine_name=self.routine_name,
            add_routine_details=self.routine,
            routine_no="ILMS-RT-01",
            routine_description="Inspect hydraulic system consumable spares.",
            by_whom="Engineering Department",
        )

    def test_create_ilms_item(self):
        payload = {
            "item_code": "ILMS-1002",
            "section_head": "ENGINEERING",
            "item_desc": "SEA WATER PUMP KIT",
            "country_code": "IN",
            "item_deno": "NOS",
            "months_shelf_life": 18,
            "crp_category": "C",
            "ved_category": "E",
            "abc_category": "B",
            "review_sub_section_code": "ENG",
            "incat_yn": True,
        }

        response = self.client.post("/api/v1/ilms/items/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Item.objects.filter(item_code="ILMS-1002").exists())

    def test_search_item_by_description(self):
        Item.objects.create(
            item_code="ILMS-2001",
            section_head="ELECTRICAL",
            item_desc="RADAR POWER SUPPLY",
            country_code="IN",
            item_deno="NOS",
            months_shelf_life=12,
            crp_category="C",
            ved_category="V",
            abc_category="A",
            review_sub_section_code="ELEC",
            incat_yn=True,
        )

        response = self.client.get("/api/v1/ilms/items/?q=hydraulic")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["item_code"], "ILMS-1001")

    def test_search_vendor_by_name(self):
        Vendor.objects.create(
            vendor_code="VEN-002",
            name="GENERAL HARDWARE STORE",
            vendor_class="LOCAL",
            country_code="IN",
        )

        response = self.client.get("/api/v1/ilms/vendors/?q=naval")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["vendor_code"], "VEN-001")

    def test_create_mo_mapping(self):
        payload = {
            "ilms_spare_id": self.item.item_code,
            "vendor_id": self.vendor.vendor_code,
            "equipment": self.ship_equipment.pk,
        }

        response = self.client.post(
            "/api/v1/ilms/mo-mappings/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        mapping = MoMappingTable.objects.get(id=response.data["id"])
        self.assertEqual(mapping.ilms_spare_id_id, self.item.item_code)
        self.assertEqual(mapping.vendor_id_id, self.vendor.vendor_code)
        self.assertEqual(mapping.equipment, self.ship_equipment)

    def test_create_demand_details(self):
        payload = {
            "vendor_id": self.vendor.vendor_code,
            "ilms_spare_id": self.item.item_code,
            "in_progress_status": "draft",
            "demand_number": "MO-DEM-001",
            "is_demand": True,
            "is_sync": False,
            "is_hod": False,
            "is_hod_approval": False,
        }

        response = self.client.post("/api/v1/ilms/demands/", payload, format="json")

        self.assertEqual(response.status_code, 201)
        demand = DemandDetails.objects.get(id=response.data["id"])
        self.assertEqual(demand.vendor_id_id, self.vendor.vendor_code)
        self.assertEqual(demand.ilms_spare_id_id, self.item.item_code)
        self.assertEqual(demand.demand_number, "MO-DEM-001")

    def test_create_planned_spares_description_for_ems_routine(self):
        response = self.client.post(
            "/api/v1/ilms/planned-descriptions/",
            {
                "item_id": self.item.item_code,
                "routine_description_id": self.routine_description.pk,
                "is_deleted": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        planned_description = MOPlannedSparesDescription.objects.get(
            id=response.data["id"]
        )
        self.assertEqual(
            planned_description.routine_description_id,
            self.routine_description,
        )

    def test_reject_invalid_dart_mo_ids(self):
        payload = {
            "equipment_id": 1000000,
            "dart_id": 1000000,
            "mo_spare": self.item.item_code,
            "pattern": "MO-PN-001",
            "description": "MO DART linked spare",
            "quantity": 1,
            "is_delete": False,
        }

        response = self.client.post(
            "/api/v1/ilms/dart-mo-spares/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("equipment_id", response.data)
        self.assertIn("dart_id", response.data)

    def test_create_dart_mo_spare_with_existing_relations(self):
        response = self.client.post(
            "/api/v1/ilms/dart-mo-spares/",
            {
                "equipment_id": self.ship_equipment.pk,
                "dart_id": self.dart.pk,
                "mo_spare": self.item.item_code,
                "pattern": "MO-PN-002",
                "description": "MO spare linked with ship equipment and DART",
                "quantity": 1,
                "is_delete": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        dart_spare = DartMOSpare.objects.get(pk=response.data["id"])
        self.assertEqual(dart_spare.equipment_id, self.ship_equipment)
        self.assertEqual(dart_spare.dart_id, self.dart)

    def test_customer_equipment_uses_sfd_equipment(self):
        customer = Customer.objects.create(
            customer_code="SHIP-001",
            name="INS Test Ship",
            customer_type="SHIP",
            mother_depot="MO",
            addressee="Logistics Officer",
            address_line1="Naval Base",
            city="Mumbai",
            state="Maharashtra",
            pin_code="400001",
            allowance_annual_rs="100000.00",
            date_introduced="2026-06-05",
            admin_authority="Command",
            station_code="MUM",
            added_by="store-user",
        )

        customer_equipment = CustomerEquipment.objects.create(
            customer=customer,
            equipment=self.equipment,
            qty_ship_fit=2,
            qty_present=2,
            date_quantity_present="2026-06-05",
            added_by="store-user",
            datetime_added="2026-06-05T10:00:00Z",
        )
        equipment_line = CustomerEquipmentLine.objects.create(
            customer=customer,
            equipment=self.equipment,
            eqpt_serial_number="EQ-SERIAL-001",
            position_specific_yn=False,
            fitment_port_stbd="PORT",
            rotation_rl="RIGHT",
            eqpt_nomenclature="Hydraulic Pump",
            generic_code="HYD-PUMP",
            eqpt_type="PUMP",
            manufacturer_name="OEM",
            supplier_name="Supplier",
            location_code="ENG-01",
            location_onboard="Engine Room",
            location_fit="PORT",
            added_by="store-user",
            datetime_added="2026-06-05T10:00:00Z",
        )

        self.assertEqual(customer_equipment.equipment, self.equipment)
        self.assertEqual(equipment_line.equipment, self.equipment)

    def test_ilms_routes_are_available(self):
        paths = [
            "/api/v1/ilms/items/",
            "/api/v1/ilms/vendors/",
            "/api/v1/ilms/mo-mappings/",
            "/api/v1/ilms/surveys/",
            "/api/v1/ilms/pts/",
            "/api/v1/ilms/demands/",
            "/api/v1/ilms/dart-mo-spares/",
            "/api/v1/ilms/iif/",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(resolve(path))

    def test_item_excel_import_and_export(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            [
                "item_code",
                "section_head",
                "item_desc",
                "country_code",
                "item_deno",
                "months_shelf_life",
                "crp_category",
                "ved_category",
                "abc_category",
                "review_sub_section_code",
                "incat_yn",
            ]
        )
        worksheet.append(
            [
                "ILMS-XLSX-01",
                "ENGINEERING",
                "Excel imported hydraulic seal",
                "IN",
                "NOS",
                12,
                "C",
                "V",
                "A",
                "ENG",
                True,
            ]
        )
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            "/api/v1/ilms/items/import-excel/",
            {
                "file": SimpleUploadedFile(
                    "items.xlsx",
                    content.getvalue(),
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Item.objects.filter(item_code="ILMS-XLSX-01").exists())
        export_response = self.client.get("/api/v1/ilms/items/export-excel/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("spreadsheetml", export_response["Content-Type"])

    def test_dashboard_reports_mo_inventory_workflow_counts(self):
        SurveyDetails.objects.create(
            ilms_spare_id=self.item,
            in_progress_status="Pending",
        )
        PTSDetails.objects.create(
            ilms_spare_id=self.item,
            in_progress_status="PTS",
            is_hod=True,
        )
        DemandDetails.objects.create(
            ilms_spare_id=self.item,
            demand_number="MO-DEM-DASH-1",
            in_progress_status="Demand",
            is_hod=True,
            is_hod_approval=True,
        )

        response = self.client.get("/api/v1/ilms/items/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["items"], 1)
        self.assertEqual(response.data["vendors"], 1)
        self.assertEqual(response.data["pending_surveys"], 1)
        self.assertEqual(response.data["hod_inbox"], 2)
        self.assertEqual(response.data["approved_actions"], 1)

    def test_planned_spare_can_be_added_to_survey_cart(self):
        planned_description = MOPlannedSparesDescription.objects.create(
            item_id=self.item,
            routine_description_id=self.routine_description,
        )
        planned_spare = PlannedMOSpareList.objects.create(
            pattern_number=self.item.item_code,
            planned_spares_description=planned_description,
            quantity_required=2,
        )

        response = self.client.post(
            "/api/v1/ilms/surveys/add-to-cart/",
            {
                "source": "planned",
                "source_ids": [planned_spare.pk],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        survey = SurveyDetails.objects.get(ilms_spare_id=self.item)
        self.assertEqual(survey.in_progress_status, "Pending")
        self.assertFalse(survey.is_hod)

    def test_demand_can_be_sent_and_approved_by_hod(self):
        demand = DemandDetails.objects.create(
            vendor_id=self.vendor,
            ilms_spare_id=self.item,
            demand_number="MO-DEM-APP-1",
            in_progress_status="Pending",
        )

        send_response = self.client.post(
            f"/api/v1/ilms/demands/{demand.pk}/send-for-approval/"
        )
        approve_response = self.client.post(
            f"/api/v1/ilms/demands/{demand.pk}/approve/"
        )

        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(approve_response.status_code, 200)
        demand.refresh_from_db()
        self.assertTrue(demand.is_hod)
        self.assertTrue(demand.is_hod_approval)
        self.assertEqual(demand.in_progress_status, "Approved")

    def test_hod_inbox_and_outbox_filter_workflow_records(self):
        pending = PTSDetails.objects.create(
            ilms_spare_id=self.item,
            in_progress_status="PTS",
            is_hod=True,
        )
        approved = SurveyDetails.objects.create(
            ilms_spare_id=self.item,
            in_progress_status="Approved",
            is_hod=True,
            is_hod_approval=True,
        )

        inbox_response = self.client.get("/api/v1/ilms/pts/inbox/")
        outbox_response = self.client.get("/api/v1/ilms/surveys/outbox/")

        self.assertEqual(inbox_response.status_code, 200)
        self.assertEqual(inbox_response.data[0]["id"], pending.pk)
        self.assertEqual(outbox_response.status_code, 200)
        self.assertEqual(outbox_response.data[0]["id"], approved.pk)

    def test_obs_spares_can_be_added_to_iif_cart_without_duplicates(self):
        from obs.models import (
            Authority,
            EquipmentClass,
            SpareClass,
            Spares,
        )

        spare_class = SpareClass.objects.create(name="MO CLASS")
        equipment_class = EquipmentClass.objects.create(
            name="MO EQUIPMENT",
            spare_class=spare_class,
        )
        authority = Authority.objects.create(name="MO")
        spare = Spares.objects.create(
            equipment_class=equipment_class,
            pattern_number="OBS-IIF-1",
            description="Not incatted item",
            quantity_authorised=1,
            quantity_available=1,
            authority=authority,
        )

        first_response = self.client.post(
            "/api/v1/ilms/iif/add-items/",
            {"spare_ids": [spare.pk]},
            format="json",
        )
        second_response = self.client.post(
            "/api/v1/ilms/iif/add-items/",
            {"spare_ids": [spare.pk]},
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(IIF.objects.filter(spare_id=spare).count(), 1)

    def test_demand_number_generation_and_receive_queue(self):
        demand = DemandDetails.objects.create(
            vendor_id=self.vendor,
            ilms_spare_id=self.item,
            in_progress_status="Approved",
            is_hod=True,
            is_hod_approval=True,
        )

        number_response = self.client.post(
            f"/api/v1/ilms/demands/{demand.pk}/generate-number/"
        )
        queue_response = self.client.get("/api/v1/ilms/demands/receive-queue/")

        self.assertEqual(number_response.status_code, 200)
        self.assertEqual(
            number_response.data["demand_number"],
            f"MO-DEMAND-{demand.pk:06d}",
        )
        self.assertEqual(queue_response.status_code, 200)
        self.assertEqual(queue_response.data[0]["id"], demand.pk)

    def test_workflow_record_can_be_completed_and_marked_synced(self):
        survey = SurveyDetails.objects.create(
            ilms_spare_id=self.item,
            in_progress_status="Approved",
            is_hod=True,
            is_hod_approval=True,
        )

        complete_response = self.client.post(
            f"/api/v1/ilms/surveys/{survey.pk}/complete/"
        )
        sync_response = self.client.post(
            f"/api/v1/ilms/surveys/{survey.pk}/mark-synced/"
        )

        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(sync_response.status_code, 200)
        survey.refresh_from_db()
        self.assertTrue(survey.is_survey)
        self.assertTrue(survey.is_sync)
        self.assertEqual(survey.in_progress_status, "Synced")

    def test_item_context_returns_mapping_and_workflow_history(self):
        MoMappingTable.objects.create(
            ilms_spare_id=self.item,
            vendor_id=self.vendor,
            equipment=self.ship_equipment,
        )
        DemandDetails.objects.create(
            ilms_spare_id=self.item,
            vendor_id=self.vendor,
            demand_number="MO-HISTORY-1",
        )

        response = self.client.get(f"/api/v1/ilms/items/{self.item.pk}/context/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["item"]["item_code"], "ILMS-1001")
        self.assertEqual(len(response.data["mappings"]), 1)
        self.assertEqual(len(response.data["demands"]), 1)

    def test_routine_lookup_returns_planned_mo_spares(self):
        planned_description = MOPlannedSparesDescription.objects.create(
            item_id=self.item,
            routine_description_id=self.routine_description,
        )
        PlannedMOSpareList.objects.create(
            pattern_number=self.item.item_code,
            planned_spares_description=planned_description,
            quantity_required=4,
        )

        response = self.client.get(
            "/api/v1/ilms/planned-spares/by-routine/",
            {"routine_description": self.routine_description.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["pattern_number"], "ILMS-1001")
        self.assertEqual(response.data[0]["quantity_required"], 4)

    def test_demand_consolidation_groups_pending_records_by_item(self):
        DemandDetails.objects.create(
            ilms_spare_id=self.item,
            vendor_id=self.vendor,
            in_progress_status="Pending",
        )
        DemandDetails.objects.create(
            ilms_spare_id=self.item,
            vendor_id=self.vendor,
            in_progress_status="Pending",
        )

        response = self.client.get("/api/v1/ilms/demands/consolidation/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["item_code"], "ILMS-1001")
        self.assertEqual(response.data[0]["record_count"], 2)

    def test_planned_cart_preserves_mo_routine_context(self):
        planned_description = MOPlannedSparesDescription.objects.create(
            item_id=self.item,
            routine_description_id=self.routine_description,
        )
        planned_spare = PlannedMOSpareList.objects.create(
            pattern_number=self.item.item_code,
            planned_spares_description=planned_description,
            quantity_required=2,
        )

        response = self.client.post(
            "/api/v1/ilms/surveys/add-to-cart/",
            {"source": "planned", "source_ids": [planned_spare.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        survey = SurveyDetails.objects.get(pk=response.data[0]["id"])
        self.assertEqual(survey.custom_user, self.user)
        self.assertEqual(survey.mo_routine_plan, planned_description)
        self.assertIsNone(survey.mo_dart)

    def test_dart_cart_preserves_mo_dart_context(self):
        dart_spare = DartMOSpare.objects.create(
            dart_id=self.dart,
            equipment_id=self.ship_equipment,
            mo_spare=self.item,
            pattern=self.item.item_code,
            description=self.item.item_desc,
            quantity=1,
        )

        response = self.client.post(
            "/api/v1/ilms/demands/add-to-cart/",
            {"source": "dart", "source_ids": [dart_spare.pk]},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        demand = DemandDetails.objects.get(pk=response.data[0]["id"])
        self.assertEqual(demand.custom_user, self.user)
        self.assertEqual(demand.mo_dart, dart_spare)
        self.assertEqual(demand.mo_status, "Pending")

    def test_ilms_bulk_hod_actions_update_reference_status_fields(self):
        pts = PTSDetails.objects.create(
            ilms_spare_id=self.item,
            vendor_id=self.vendor,
            in_progress_status="Pending",
        )

        send_response = self.client.post(
            "/api/v1/ilms/pts/bulk-send-for-approval/",
            {"ids": [pts.pk]},
            format="json",
        )
        approve_response = self.client.post(
            "/api/v1/ilms/pts/bulk-approve/",
            {"ids": [pts.pk]},
            format="json",
        )

        self.assertEqual(send_response.status_code, 200)
        self.assertEqual(approve_response.status_code, 200)
        pts.refresh_from_db()
        self.assertTrue(pts.is_hod)
        self.assertTrue(pts.is_hod_approval)
        self.assertEqual(pts.mo_pts_status, "Approved")

    def test_ilms_search_helper_aliases_return_expected_data(self):
        item_response = self.client.get(
            "/api/v1/ilms/items/search-list/",
            {"q": "hydraulic"},
        )
        vendor_response = self.client.get(
            "/api/v1/ilms/vendors/search-list/",
            {"q": "naval"},
        )

        self.assertEqual(item_response.status_code, 200)
        self.assertEqual(vendor_response.status_code, 200)
        self.assertEqual(item_response.data[0]["item_code"], self.item.item_code)
        self.assertEqual(
            vendor_response.data[0]["vendor_code"], self.vendor.vendor_code
        )
