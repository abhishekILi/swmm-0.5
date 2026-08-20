from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from master.models import Department

from .models import (
    AddRoutineDetails,
    EquipmentName,
    FussRaiseDetails,
    RoutineDescription,
    SectionName,
    UniqueRoutineName,
)


class EMSReferenceParityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        department = Department.objects.create(name="Engineering", code="ENG")
        self.user = get_user_model().objects.create_user(
            username="ems-user",
            password="pass",
            department=department,
        )
        self.client.force_authenticate(self.user)
        section = SectionName.objects.create(name="Propulsion", department=department)
        equipment = EquipmentName.objects.create(
            name="GT Engine",
            equipment_code="GT-001",
            section=section,
        )
        routine_name = UniqueRoutineName.objects.create(name="Lube Oil Check")
        add_routine = AddRoutineDetails.objects.create(
            equipment_name=equipment,
            routine_name=routine_name,
            by_whom="SS",
            routine_category="CALENDAR BASED",
            frequency="MONTHLY",
        )
        self.routine = RoutineDescription.objects.create(
            equipment_name=equipment,
            routine_name=routine_name,
            add_routine_details=add_routine,
            routine_no="R-001",
            routine_description="Check lube oil level",
            by_whom="SS",
            maintop_no="MTP-001",
        )

    def test_mul_raise_fuss_persists_reference_new_equipment_flag(self):
        response = self.client.post(
            reverse("ems:mulraisefuss"),
            {
                "selected_ids": [self.routine.pk],
                "ship": "INS TEST",
                "department": "ENG",
                "serial_no": "FUSS-001",
                "equipment": "GT Engine",
                "maintop_no": "MTP-001",
                "frequency": "MONTHLY",
                "new_equipment": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        fuss = FussRaiseDetails.objects.get()
        self.assertTrue(fuss.new_equipment)
        self.routine.refresh_from_db()
        self.assertTrue(self.routine.is_fuss)

    def test_reference_ems_alias_routes_are_available(self):
        alias_names = [
            "complete_routine",
            "search_detail_planned",
            "search_detail_planned_pk",
            "save_oem_spare_legacy",
            "history_close_routine_legacy",
            "routine_init_data",
            "save_routine_init",
            "generatedl1",
            "generatedl1_list",
            "report_inner_rows",
        ]

        for name in alias_names:
            kwargs = {"pk": self.routine.pk} if name.endswith("_pk") else {}
            if name in {"complete_routine"}:
                kwargs = {"pk": self.routine.pk}
            if name == "report_inner_rows":
                kwargs = {"id": 1}
            with self.subTest(name=name):
                self.assertTrue(reverse(f"ems:{name}", kwargs=kwargs))
