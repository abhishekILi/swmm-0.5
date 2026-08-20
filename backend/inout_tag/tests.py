from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import resolve
from django.utils import timezone
from master.models import Department
from openpyxl import Workbook
from rest_framework.test import APIClient
from sfd.models import ShipEquipment

from .models import TagIn, TagInApproval, TagOut


class InOutTagApiFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.engineering_department = Department.objects.create(
            name="Engineering",
            code="ENG",
        )
        self.electrical_department = Department.objects.create(
            name="Electrical",
            code="ELEC",
        )
        self.operations_department = Department.objects.create(
            name="Operations",
            code="OPS",
        )
        self.user = get_user_model().objects.create_user(
            username="tag-manager",
            password="Pass@12345",
            is_staff=True,
            department=self.engineering_department,
        )
        self.client.force_authenticate(self.user)
        self.tagout_equipment = ShipEquipment.objects.create(
            nomenclature="Hydraulic Pressure Valve",
            equipment_serial_no="HV-001",
        )
        self.new_tagout_equipment = ShipEquipment.objects.create(
            nomenclature="Fire Control Panel",
            equipment_serial_no="FCS-001",
        )
        self.tagout = TagOut.objects.create(
            date="2026-06-04",
            tagout_equipment_name=self.tagout_equipment,
            name_of_subsystem="HYDRAULIC SYSTEM",
            name_of_component="PRESSURE VALVE",
            serial_number_of_component="HV-001",
            pattern_number_of_component="PN-HV-001",
            weight_of_component="12.50",
            type="danger",
            condition="non_ops",
            special_instructions="Keep system isolated",
            expected_date_of_tagin="2026-06-10",
            tagout_reason="repair_or_overhauling",
            tagout_description="Valve removed for repair",
            tagout_maintainer_name_rank="PO TECH",
        )
        self.tagout.departments_affected.set(
            [
                self.engineering_department,
                self.electrical_department,
            ]
        )

    def test_ship_equipment_actions_return_ordered_options(self):
        expected = [
            {
                "id": self.new_tagout_equipment.id,
                "nomenclature": self.new_tagout_equipment.nomenclature,
            },
            {
                "id": self.tagout_equipment.id,
                "nomenclature": self.tagout_equipment.nomenclature,
            },
        ]

        tagout_response = self.client.get(
            "/api/v1/inout-tags/tag-outs/ship_equipments/"
        )
        tagin_response = self.client.get("/api/v1/inout-tags/tag-ins/ship_equipments/")

        self.assertEqual(tagout_response.status_code, 200)
        self.assertEqual(tagin_response.status_code, 200)
        self.assertEqual(tagout_response.data["ship_equipments"], expected)
        self.assertEqual(tagin_response.data["ship_equipments"], expected)

    def test_tagout_excel_import_and_export(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["date", "name_of_component", "type", "condition"])
        worksheet.append(["2026-06-06", "COOLING WATER VALVE", "warning", "non_ops"])
        content = BytesIO()
        workbook.save(content)

        response = self.client.post(
            "/api/v1/inout-tags/tag-outs/import-excel/",
            {
                "file": SimpleUploadedFile(
                    "tagouts.xlsx",
                    content.getvalue(),
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            TagOut.objects.filter(name_of_component="COOLING WATER VALVE").exists()
        )
        export_response = self.client.get("/api/v1/inout-tags/tag-outs/export-excel/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("spreadsheetml", export_response["Content-Type"])

    def test_create_tagout_generates_tag_number(self):
        payload = {
            "date": "2026-06-04",
            "tagout_equipment_name": self.new_tagout_equipment.pk,
            "name_of_subsystem": "FIRE CONTROL SYSTEM",
            "name_of_component": "CONTROL PANEL",
            "serial_number_of_component": "FCS-001",
            "pattern_number_of_component": "PN-FCS-001",
            "weight_of_component": "18.25",
            "type": "warning",
            "condition": "partially_ops",
            "special_instructions": "Operate in standby only",
            "departments_affected": [self.operations_department.pk],
            "expected_date_of_tagin": "2026-06-12",
            "tagout_reason": "survey_and_demand",
            "tagout_description": "Panel tagged out for survey",
            "tagout_maintainer_name_rank": "CPO TECH",
        }

        response = self.client.post(
            "/api/v1/inout-tags/tag-outs/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["tagout_number"].startswith("TAG-"))
        self.assertEqual(response.data["approval_status"], "in_progress")
        self.assertEqual(
            response.data["tagout_equipment_name"],
            self.new_tagout_equipment.pk,
        )
        # The creator's own department (Engineering) is always auto-included
        # alongside whatever was explicitly submitted (Operations).
        self.assertCountEqual(
            response.data["departments_affected"],
            [self.operations_department.pk, self.engineering_department.pk],
        )

    def test_create_tagout_requires_department(self):
        no_department_user = get_user_model().objects.create_user(
            username="no-department-user",
            password="Pass@12345",
        )
        self.client.force_authenticate(no_department_user)

        response = self.client.post(
            "/api/v1/inout-tags/tag-outs/",
            {
                "date": "2026-06-04",
                "tagout_equipment_name": self.new_tagout_equipment.pk,
                "name_of_component": "CONTROL PANEL",
                "type": "warning",
                "tagout_reason": "survey_and_demand",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_tagout_numbers_use_the_next_yearly_sequence(self):
        year = timezone.now().year

        second_tagout = TagOut.objects.create(
            date="2026-06-05",
            tagout_equipment_name=self.new_tagout_equipment,
            name_of_component="CONTROL PANEL",
        )

        self.assertEqual(self.tagout.tagout_number, f"TAG-{year}-001")
        self.assertEqual(second_tagout.tagout_number, f"TAG-{year}-002")

    def test_approve_tagout_updates_status_and_time(self):
        response = self.client.post(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.tagout.refresh_from_db()
        self.assertEqual(self.tagout.approval_status, "approved")
        self.assertIsNotNone(self.tagout.approved_on)

    def test_tagout_approval_rejects_unknown_status(self):
        response = self.client.post(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            {"approval_status": "closed"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("approval_status", response.data)
        self.tagout.refresh_from_db()
        self.assertEqual(self.tagout.approval_status, "in_progress")

    def test_create_tagin_against_tagout(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])
        payload = {
            "tagout": self.tagout.id,
            "tagin_date": "2026-06-08",
            "tagin_description": "Valve fitted back after repair",
            "tagin_maintainer": "PO TECH",
            "all_items_returned": True,
            "status": "completed",
            "approval_status": "pending",
            "tagin_remarks": "Ready for department approval",
            "tagin_maintainer_name_rank": "PO TECH",
        }

        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        tagin = TagIn.objects.get(id=response.data["id"])
        self.assertEqual(tagin.tagout_id, self.tagout.id)
        self.assertEqual(tagin.approval_status, "pending")

    def test_reject_duplicate_tagin_for_same_tagout(self):
        TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="First tag in entry",
            tagin_maintainer="PO TECH",
        )
        payload = {
            "tagout": self.tagout.id,
            "tagin_date": "2026-06-09",
            "tagin_description": "Duplicate tag in entry",
            "tagin_maintainer": "PO TECH",
        }

        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("tagout", response.data)

    def test_tagin_viewset_has_no_approve_action(self):
        """
        TagIn no longer exposes a top-level approve action -- it bypassed the
        per-department TagInApproval workflow and has no reference equivalent.
        Approval only happens per-department via /tag-in-approvals/.
        """
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve fitted back after repair",
            tagin_maintainer="PO TECH",
        )

        response = self.client.post(
            f"/api/v1/inout-tags/tag-ins/{tagin.id}/approve/",
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_tagin_approval_sets_pending_until_all_departments_approve(self):
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve fitted back after repair",
            tagin_maintainer="PO TECH",
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.engineering_department,
            approval_status="approved",
            approved_on=timezone.now(),
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.electrical_department,
            approval_status="pending",
        )

        tagin.check_all_approvals()

        tagin.refresh_from_db()
        self.assertEqual(tagin.approval_status, "pending")

    def test_approval_api_records_approver_and_time(self):
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve fitted back after repair",
            tagin_maintainer="PO TECH",
        )

        response = self.client.post(
            "/api/v1/inout-tags/tag-in-approvals/",
            {
                "tagin": tagin.pk,
                "department": self.engineering_department.pk,
                "approval_status": "approved",
                "remarks": "Department clearance complete",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        approval = TagInApproval.objects.get(pk=response.data["id"])
        self.assertEqual(approval.approved_by, self.user)
        self.assertIsNotNone(approval.approved_on)

    def test_tagin_approval_marks_approved_when_all_departments_approve(self):
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve fitted back after repair",
            tagin_maintainer="PO TECH",
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.engineering_department,
            approval_status="approved",
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.electrical_department,
            approval_status="approved",
        )

        tagin.check_all_approvals()

        tagin.refresh_from_db()
        self.assertEqual(tagin.approval_status, "approved")

    def test_tagin_approval_marks_rejected_if_any_department_rejects(self):
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve fitted back after repair",
            tagin_maintainer="PO TECH",
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.engineering_department,
            approval_status="approved",
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.electrical_department,
            approval_status="rejected",
            remarks="Department clearance pending",
        )

        tagin.check_all_approvals()

        tagin.refresh_from_db()
        self.assertEqual(tagin.approval_status, "rejected")

    def test_reject_duplicate_department_approval(self):
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve fitted back after repair",
            tagin_maintainer="PO TECH",
        )
        TagInApproval.objects.create(
            tagin=tagin,
            department=self.engineering_department,
            approval_status="pending",
        )
        payload = {
            "tagin": tagin.id,
            "department": self.engineering_department.pk,
            "approval_status": "approved",
            "remarks": "Duplicate approval should not be allowed",
        }

        response = self.client.post(
            "/api/v1/inout-tags/tag-in-approvals/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.data)

    def test_inout_tag_routes_are_available(self):
        paths = [
            "/api/v1/inout-tags/tag-outs/",
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/",
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            "/api/v1/inout-tags/tag-ins/",
            "/api/v1/inout-tags/tag-in-approvals/",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(resolve(path))

    def test_tagin_can_only_be_created_for_an_approved_tagout(self):
        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            {
                "tagout": self.tagout.pk,
                "tagin_date": "2026-06-08",
                "tagin_description": "Valve restored after repair",
                "tagin_maintainer": "PO TECH",
                "all_items_returned": True,
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("tagout", response.data)

    def test_pending_items_are_required_when_not_all_items_returned(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])

        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            {
                "tagout": self.tagout.pk,
                "tagin_date": "2026-06-08",
                "tagin_description": "Valve partly restored",
                "tagin_maintainer": "PO TECH",
                "all_items_returned": False,
                "items_pending": "",
                "status": "in_progress",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("items_pending", response.data)

    def test_creating_tagin_adds_approvals_for_affected_departments(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])

        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            {
                "tagout": self.tagout.pk,
                "tagin_date": "2026-06-08",
                "tagin_description": "Valve restored after repair",
                "tagin_maintainer": "PO TECH",
                "all_items_returned": True,
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        tagin = TagIn.objects.get(pk=response.data["id"])
        approvals = tagin.tagin_approvals.order_by("department__code")
        self.assertEqual(approvals.count(), 2)
        self.assertEqual(
            set(approvals.values_list("department__code", flat=True)),
            {"ELEC", "ENG"},
        )

    def test_department_approval_immediately_updates_tagin_status(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve restored after repair",
            tagin_maintainer="PO TECH",
        )
        engineering = TagInApproval.objects.create(
            tagin=tagin,
            department=self.engineering_department,
        )
        electrical = TagInApproval.objects.create(
            tagin=tagin,
            department=self.electrical_department,
        )

        first_response = self.client.patch(
            (f"/api/v1/inout-tags/tag-in-approvals/{engineering.pk}/"),
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)
        tagin.refresh_from_db()
        self.assertEqual(tagin.approval_status, "pending")

        second_response = self.client.patch(
            (f"/api/v1/inout-tags/tag-in-approvals/{electrical.pk}/"),
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(second_response.status_code, 200)
        tagin.refresh_from_db()
        self.assertEqual(tagin.approval_status, "approved")

    def test_dashboard_and_history_report_current_tag_activity(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])
        TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve restored after repair",
            tagin_maintainer="PO TECH",
        )

        dashboard_response = self.client.get("/api/v1/inout-tags/tag-outs/dashboard/")
        history_response = self.client.get(
            "/api/v1/inout-tags/tag-outs/history/",
            {
                "department": self.engineering_department.pk,
                "approval_status": "approved",
            },
        )

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(dashboard_response.data["approved_tagouts"], 1)
        self.assertEqual(dashboard_response.data["tagins"], 1)
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.data), 1)
        self.assertEqual(
            history_response.data[0]["tagout_number"],
            self.tagout.tagout_number,
        )

    def test_eligible_for_tagin_lists_only_approved_open_tagouts(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])
        rejected = TagOut.objects.create(
            date="2026-06-05",
            tagout_equipment_name=self.new_tagout_equipment,
            name_of_component="CONTROL PANEL",
            approval_status="rejected",
        )

        response = self.client.get("/api/v1/inout-tags/tag-outs/eligible-for-tagin/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.tagout.pk)
        self.assertNotEqual(response.data[0]["id"], rejected.pk)


class InOutTagAuthorizationTests(TestCase):
    """
    Department/role-based authorization and visibility scoping, ported from
    reference's addtagout/approvetagot/add_tagin/approvetagin/tagoutlist/tag_in.
    Uses non-staff users so the staff-override bypass doesn't mask the checks.
    """

    def setUp(self):
        self.client = APIClient()
        self.engineering_department = Department.objects.create(
            name="Engineering",
            code="ENG",
        )
        self.electrical_department = Department.objects.create(
            name="Electrical",
            code="ELEC",
        )
        self.equipment = ShipEquipment.objects.create(
            nomenclature="Hydraulic Pressure Valve",
            equipment_serial_no="HV-001",
        )

        self.eng_tech = get_user_model().objects.create_user(
            username="eng-tech",
            password="Pass@12345",
            department=self.engineering_department,
        )
        self.eng_hod = get_user_model().objects.create_user(
            username="eng-hod",
            password="Pass@12345",
            department=self.engineering_department,
            designation="Head of Department",
        )
        self.eng_dyhod = get_user_model().objects.create_user(
            username="eng-dyhod",
            password="Pass@12345",
            department=self.engineering_department,
            designation="DY HOD",
        )
        self.elec_hod = get_user_model().objects.create_user(
            username="elec-hod",
            password="Pass@12345",
            department=self.electrical_department,
            designation="Head of Department",
        )

        self.tagout = TagOut.objects.create(
            date="2026-06-04",
            tagout_equipment_name=self.equipment,
            name_of_component="PRESSURE VALVE",
            type="danger",
            user_profile=self.eng_tech,
        )
        self.tagout.departments_affected.set([self.engineering_department])

    def test_regular_user_cannot_approve_tagout(self):
        self.client.force_authenticate(self.eng_tech)

        response = self.client.post(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_hod_of_different_department_cannot_approve_tagout(self):
        self.client.force_authenticate(self.elec_hod)

        response = self.client.post(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            {"approval_status": "approved"},
            format="json",
        )

        # Row-visibility scoping (matching reference's own department-scoped
        # .get() lookup) hides other departments' tagouts entirely, so a
        # cross-department attempt reads as "not found", not "forbidden".
        self.assertEqual(response.status_code, 404)

    def test_dyhod_of_same_department_can_approve_tagout(self):
        self.client.force_authenticate(self.eng_dyhod)

        response = self.client.post(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.tagout.refresh_from_db()
        self.assertEqual(self.tagout.approval_status, "approved")
        self.assertEqual(self.tagout.approved_by, self.eng_dyhod)

    def test_hod_of_same_department_can_approve_tagout(self):
        self.client.force_authenticate(self.eng_hod)

        response = self.client.post(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/approve/",
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

    def test_tagout_list_scoped_by_department_for_hod(self):
        other_tagout = TagOut.objects.create(
            date="2026-06-05",
            tagout_equipment_name=self.equipment,
            name_of_component="OTHER COMPONENT",
            user_profile=self.elec_hod,
        )

        self.client.force_authenticate(self.eng_hod)
        response = self.client.get("/api/v1/inout-tags/tag-outs/")

        ids = {row["id"] for row in response.data}
        self.assertIn(self.tagout.id, ids)
        self.assertNotIn(other_tagout.id, ids)

    def test_tagout_list_scoped_to_own_records_for_regular_user(self):
        other_user_tagout = TagOut.objects.create(
            date="2026-06-05",
            tagout_equipment_name=self.equipment,
            name_of_component="OTHER COMPONENT",
            user_profile=self.eng_hod,
        )

        self.client.force_authenticate(self.eng_tech)
        response = self.client.get("/api/v1/inout-tags/tag-outs/")

        ids = {row["id"] for row in response.data}
        self.assertIn(self.tagout.id, ids)
        self.assertNotIn(other_user_tagout.id, ids)

    def test_only_tagout_creator_can_file_tagin(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])

        self.client.force_authenticate(self.eng_hod)
        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            {
                "tagout": self.tagout.pk,
                "tagin_date": "2026-06-08",
                "tagin_description": "Valve restored after repair",
                "tagin_maintainer": "PO TECH",
                "all_items_returned": True,
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_tagout_creator_can_file_tagin(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])

        self.client.force_authenticate(self.eng_tech)
        response = self.client.post(
            "/api/v1/inout-tags/tag-ins/",
            {
                "tagout": self.tagout.pk,
                "tagin_date": "2026-06-08",
                "tagin_description": "Valve restored after repair",
                "tagin_maintainer": "PO TECH",
                "all_items_returned": True,
                "status": "completed",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def _make_tagin_with_approval(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])
        tagin = TagIn.objects.create(
            tagout=self.tagout,
            tagin_date="2026-06-08",
            tagin_description="Valve restored after repair",
            tagin_maintainer="PO TECH",
        )
        return tagin, TagInApproval.objects.create(
            tagin=tagin,
            department=self.engineering_department,
        )

    def test_dyhod_cannot_approve_tagin(self):
        _tagin, approval = self._make_tagin_with_approval()
        self.client.force_authenticate(self.eng_dyhod)

        response = self.client.patch(
            f"/api/v1/inout-tags/tag-in-approvals/{approval.pk}/",
            {"approval_status": "approved"},
            format="json",
        )

        # DY HOD isn't an eligible tag-in approver at all (HOD only, per
        # reference), and isn't the tagout's creator either, so this approval
        # row falls outside their visibility scope entirely -- "not found".
        self.assertEqual(response.status_code, 404)

    def test_hod_of_different_department_cannot_approve_tagin(self):
        _tagin, approval = self._make_tagin_with_approval()
        self.client.force_authenticate(self.elec_hod)

        response = self.client.patch(
            f"/api/v1/inout-tags/tag-in-approvals/{approval.pk}/",
            {"approval_status": "approved"},
            format="json",
        )

        # Same reasoning as the tagout case: cross-department rows are
        # scoped out of visibility entirely, reading as "not found".
        self.assertEqual(response.status_code, 404)

    def test_hod_of_matching_department_can_approve_tagin(self):
        _tagin, approval = self._make_tagin_with_approval()
        self.client.force_authenticate(self.eng_hod)

        response = self.client.patch(
            f"/api/v1/inout-tags/tag-in-approvals/{approval.pk}/",
            {"approval_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        approval.refresh_from_db()
        self.assertEqual(approval.approved_by, self.eng_hod)

    def test_cannot_reapprove_already_processed_tagin_approval(self):
        _tagin, approval = self._make_tagin_with_approval()
        self.client.force_authenticate(self.eng_hod)
        self.client.patch(
            f"/api/v1/inout-tags/tag-in-approvals/{approval.pk}/",
            {"approval_status": "approved"},
            format="json",
        )

        response = self.client.patch(
            f"/api/v1/inout-tags/tag-in-approvals/{approval.pk}/",
            {"approval_status": "rejected"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_print_slip_requires_approved_tagout(self):
        self.client.force_authenticate(self.eng_tech)

        response = self.client.get(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/print-slip/"
        )

        self.assertEqual(response.status_code, 400)

    def test_print_slip_returns_pdf_for_creator(self):
        self.tagout.approval_status = "approved"
        self.tagout.approved_by = self.eng_hod
        self.tagout.save(update_fields=["approval_status", "approved_by"])

        self.client.force_authenticate(self.eng_tech)
        response = self.client.get(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/print-slip/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_print_slip_blocked_for_unrelated_user(self):
        self.tagout.approval_status = "approved"
        self.tagout.save(update_fields=["approval_status"])

        self.client.force_authenticate(self.elec_hod)
        response = self.client.get(
            f"/api/v1/inout-tags/tag-outs/{self.tagout.id}/print-slip/"
        )

        self.assertEqual(response.status_code, 403)
