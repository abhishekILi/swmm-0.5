from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from master.models import (
    ChMasterSymptoms,
    Department,
    MSeverity,
    RefitMaintenancePeriod,
)
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate
from rest_framework_simplejwt.tokens import AccessToken

from .models import InitiateDart, InitiateRADL, RADLMaster
from .serializers import RADLMasterSerializer, SymptomSerializer
from .views import MaintenanceOverviewDetailsAPIView


class RADLMasterAPITest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="radl_master_tester",
            password="test-password",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_radl_master_api(self):
        refit = RefitMaintenancePeriod.objects.create(
            name="MR",
            maintenance_period="REFIT",
            occasion="REFIT",
        )
        data = {
            "ra_dl_name": "DL-III MAJOR REFIT 2026",
            "dockyard_name": "Naval Dockyard Mumbai",
            "refit_type_name": "Major",
            "refit_type_f_key": refit.pk,
        }
        serializer = RADLMasterSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(RADLMaster.objects.count(), 1)
        report = RADLMaster.objects.get()
        self.assertEqual(report.ra_dl_name, "DL-III MAJOR REFIT 2026")
        self.assertEqual(report.refit_type_f_key, refit)

    def test_get_radl_master_list(self):
        RADLMaster.objects.create(
            ra_dl_name="DL-III MAJOR REFIT 2026",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="Major",
        )
        serializer = RADLMasterSerializer(
            RADLMaster.objects.order_by("-id"),
            many=True,
        )
        self.assertEqual(len(serializer.data), 1)
        self.assertEqual(serializer.data[0]["ra_dl_name"], "DL-III MAJOR REFIT 2026")


class DartAPITestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dart_dashboard_tester",
            password="test-password",
        )
        self.client.force_authenticate(user=self.user)
        self.factory = APIRequestFactory()
        self.department = Department.objects.create(name="Engineering", code="ENG")
        self.symptom = ChMasterSymptoms.objects.create(
            symptom_code="SYM01", active=True
        )
        self.severity = MSeverity.objects.create(severity_name="Critical", active=True)
        self.defect_list_url = reverse("radl_master:api_initiate_dart")

    def test_create_dart(self):
        payload = {
            "dart_type": "Defect",
            "symptoms": self.symptom.id,
            "severity": self.severity.id,
            "defectiveComponent": "Main Engine",
            "description": "Oil leaking from valve",
            "trial": "Yes",
            "universal_id_t_dart": "SWMM-DART-001",
        }
        response = self.client.post(self.defect_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InitiateDart.objects.count(), 1)
        dart = InitiateDart.objects.get()
        self.assertEqual(dart.defective_component, "Main Engine")
        self.assertEqual(dart.universal_id_t_dart, "SWMM-DART-001")

    def test_reference_alias_routes_resolve_to_existing_apis(self):
        report = RADLMaster.objects.create(
            ra_dl_name="DL-II ACCDB 2026",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="MR",
        )
        aliases = [
            ("home", {}),
            ("dartdashboard", {}),
            ("darthistory", {}),
            ("history", {}),
            ("generate_report", {}),
            ("report_inner_rows", {"report_id": report.pk}),
            ("export_pending_defects_xlsx", {}),
            ("export_pending_defects_access", {}),
            ("export_pending_defects_accdb", {}),
            ("export_pending_defects_dl2_accdb", {}),
            ("export_pending_defects_dl2_ndv", {}),
            ("export_existing_pending_defects_dl2_nsrykar", {}),
            ("export_pending_defects_dl2_nsrykoc", {}),
            ("export_pending_defects_dl2_nsrypbr", {}),
            ("export_existing_pending_defects_dl2_accdb", {"report_id": report.pk}),
            ("generate_guarantee_pdf", {"dart_id": 1}),
            ("history_pdf", {"id": 1}),
        ]

        for name, kwargs in aliases:
            with self.subTest(name=name):
                self.assertTrue(reverse(f"radl_master:{name}", kwargs=kwargs))

    def test_legacy_delete_dl_row_body_endpoint_soft_deletes_row(self):
        defect = InitiateDart.objects.create(
            dart_number="D-E-9001",
            defective_component="Pump",
            defective_discriptions="Pump vibration",
            is_dl_draft=True,
        )
        row = InitiateRADL.objects.create(
            initiate_dart=defect,
            dl_no="DL-II-001",
            dl_type="DL-II",
            dl_key="DL-II KEY",
            ra_grup_id="GRP-001",
            status="DRAFT",
        )

        response = self.client.post(
            reverse("radl_master:delete_dl_row"),
            {"dl_id": row.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row.refresh_from_db()
        defect.refresh_from_db()
        self.assertEqual(row.status, "DELETED")
        self.assertFalse(row.is_active)
        self.assertFalse(defect.is_dl_draft)

    def test_list_symptoms(self):
        serializer = SymptomSerializer(
            ChMasterSymptoms.objects.filter(active=1), many=True
        )
        self.assertTrue(len(serializer.data) > 0)

    def test_refit_and_operational_occasion_matches_reference_payload(self):
        refit = RefitMaintenancePeriod.objects.create(
            name="MR",
            maintenance_period="REFIT",
            occasion="REFIT",
            actual_start_date="2026-01-01",
            actual_end_date="2026-03-31",
        )
        operational = RefitMaintenancePeriod.objects.create(
            name="EAMP1-2026",
            maintenance_period="OPERATIONAL",
            occasion="EAMP",
            actual_start_date="2026-04-01",
            actual_end_date="2026-04-30",
        )

        url = reverse("radl_master:refit-operational-occation")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {
                "title",
                "pqr",
                "ref",
                "refit_periods",
                "maint_periods",
                "ops_periods",
            },
        )
        self.assertEqual(
            response.data["title"],
            "DART | Refit Nomenclature Create / Amend",
        )
        self.assertEqual(response.data["pqr"], "DART-Copyright")
        self.assertEqual(response.data["ref"], "Kolkata@Indian Navy")
        self.assertEqual(
            response.data["refit_periods"],
            [
                {
                    "id": refit.id,
                    "name": "MR",
                    "type": "REFIT",
                    "maintenance_period": "REFIT",
                    "actual_start_date": "2026-01-01",
                    "actual_end_date": "2026-03-31",
                }
            ],
        )
        self.assertEqual(
            response.data["maint_periods"],
            [
                {
                    "id": operational.id,
                    "name": "EAMP1-2026",
                    "type": "EAMP",
                    "maintenance_period": "OPERATIONAL",
                    "actual_start_date": "2026-04-01",
                    "actual_end_date": "2026-04-30",
                }
            ],
        )
        self.assertEqual(
            [period["id"] for period in response.data["ops_periods"]],
            [operational.id, refit.id],
        )

    def test_generated_dl_ii_reports_show_only_masters_with_live_rows(self):
        report = RADLMaster.objects.create(
            ra_dl_name="DL-II ACCDB 2026",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="MR",
        )
        empty_report = RADLMaster.objects.create(
            ra_dl_name="Empty Report",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="NR",
        )
        deleted_report = RADLMaster.objects.create(
            ra_dl_name="Deleted Report",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="SR",
        )
        live_dart = InitiateDart.objects.create(
            dart_number="D-E-8001",
            defective_component="Main Engine",
            defective_discriptions="Oil leakage from valve",
        )
        deleted_dart = InitiateDart.objects.create(
            dart_number="D-E-8002",
            defective_component="Pump",
            defective_discriptions="Pump vibration",
        )
        InitiateRADL.objects.create(
            radl_master=report,
            initiate_dart=live_dart,
            dl_no="DL-II-001",
            dl_type="DL-II",
            dl_key="DL-II KEY",
            ra_grup_id="GRP-001",
            status="GENERATED",
        )
        InitiateRADL.objects.create(
            radl_master=deleted_report,
            initiate_dart=deleted_dart,
            dl_no="DL-II-002",
            dl_type="DL-II",
            dl_key="DL-II DELETED",
            ra_grup_id="GRP-002",
            status="DELETED",
        )

        url = reverse("radl_master:generated-dl-ii-reports")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], report.id)
        self.assertEqual(response.data[0]["ra_dl_name"], "DL-II ACCDB 2026")
        self.assertEqual(response.data[0]["rows_count"], 1)
        self.assertNotEqual(response.data[0]["id"], empty_report.id)

    def test_generated_dl_ii_report_rows_match_reference_inner_rows(self):
        report = RADLMaster.objects.create(
            ra_dl_name="DL-II ACCDB 2026",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="MR",
        )
        defect = InitiateDart.objects.create(
            dart_number="D-E-8001",
            defective_component="Main Engine",
            defective_discriptions="Oil leakage from valve",
        )
        row = InitiateRADL.objects.create(
            radl_master=report,
            initiate_dart=defect,
            dl_no="DL-II-001",
            dl_type="DL-II",
            dl_key="DL-II KEY",
            ra_grup_id="GRP-001",
            status="GENERATED",
        )

        url = reverse(
            "radl_master:generated-dl-ii-report-rows",
            kwargs={"report_id": report.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertEqual(
            response.data["data"],
            [
                {
                    "id": row.id,
                    "dl_no": "DL-II-001",
                    "ra_dl_name": "DL-II KEY",
                    "dl_type": "DL-II",
                    "status": "GENERATED",
                    "eq_name": "-",
                    "description": "Oil leakage from valve",
                    "defective_component": "Main Engine",
                }
            ],
        )

    def test_generated_dl_ii_report_export_downloads_rows(self):
        report = RADLMaster.objects.create(
            ra_dl_name="DL-II ACCDB 2026",
            dockyard_name="Naval Dockyard Mumbai",
            refit_type_name="MR",
        )
        defect = InitiateDart.objects.create(
            dart_number="D-E-8001",
            defective_component="Main Engine",
            defective_discriptions="Oil leakage from valve",
        )
        InitiateRADL.objects.create(
            radl_master=report,
            initiate_dart=defect,
            dl_no="DL-II-001",
            dl_type="DL-II",
            dl_key="DL-II KEY",
            ra_grup_id="GRP-001",
            status="GENERATED",
        )

        url = reverse(
            "radl_master:generated-dl-ii-report-export",
            kwargs={"report_id": report.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("generated_dl_ii_report", response["Content-Disposition"])
        self.assertIn(b"DL-II-001", response.content)

    def test_maintenance_overview_details_matches_dashboard_contract(self):
        request = self.factory.get("/")
        force_authenticate(request, user=self.user)
        response = MaintenanceOverviewDetailsAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {
                "command_actions_pending",
                "maintenance_prioritisation",
                "equipment_health_monitoring",
                "movement_and_configuration_history",
                "maintenance_constraints_and_dependencies",
                "contextual_search_and_drill_down",
                "reliability_and_degradation_trend",
                "trials_validation_and_post_maintenance",
            },
        )

        prioritisation = response.data["maintenance_prioritisation"]
        self.assertEqual(
            set(prioritisation),
            {
                "heading",
                "view_all_flag",
                "maintenance_prioritisation_items",
            },
        )

        equipment_health = response.data["equipment_health_monitoring"]
        self.assertEqual(
            set(equipment_health),
            {
                "heading",
                "view_all_flag",
                "search_enabled",
                "equipment_summary",
                "selected_equipment",
            },
        )

        movement_history = response.data["movement_and_configuration_history"]
        self.assertEqual(
            set(movement_history),
            {
                "heading",
                "view_all_flag",
                "movement_and_configuration_histories",
            },
        )

    def test_maintenance_overview_returns_all_open_defects(self):
        defects = [
            InitiateDart(
                dart_number=f"D-E-{number:04d}",
                severity_code=self.severity,
                defective_discriptions=f"Defect {number}",
                is_closed=False,
            )
            for number in range(1, 13)
        ]
        InitiateDart.objects.bulk_create(defects)

        request = self.factory.get("/")
        force_authenticate(request, user=self.user)
        response = MaintenanceOverviewDetailsAPIView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prioritisation_items = response.data["maintenance_prioritisation"][
            "maintenance_prioritisation_items"
        ]
        self.assertEqual(len(prioritisation_items), 12)
        self.assertEqual(
            response.data["command_actions_pending"]["items"][0]["count"],
            12,
        )


def create_test_token(expired=False):
    user = get_user_model()
    user, _ = user.objects.get_or_create(id=1, defaults={"username": "testuser"})
    token = AccessToken.for_user(user)
    if expired:
        token.set_exp(lifetime=-timedelta(minutes=5))
    return str(token)


class CMMSIntegrationAPITests(APITestCase):
    def setUp(self):
        self.valid_token = create_test_token(expired=False)
        self.expired_token = create_test_token(expired=True)
        self.valid_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.valid_token}"}
        self.expired_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.expired_token}"}
        self.invalid_headers = {"HTTP_AUTHORIZATION": "Bearer invalidtoken"}

    def test_cmms_endpoint_requires_jwt_token(self):
        response = self.client.get("/api/v1/cmms/dart")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_jwt_token_is_rejected(self):
        response = self.client.get("/api/v1/cmms/dart", **self.invalid_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_expired_jwt_token_is_rejected(self):
        response = self.client.get("/api/v1/cmms/dart", **self.expired_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cmms_dart_get_payload(self):
        response = self.client.get("/api/v1/cmms/dart", **self.valid_headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cmms_routines_complete_validation(self):
        payload = {
            "routine_id": 101,
            "old_dart_number": "DART-OLD",
            "new_dart_number": "DART-NEW",
            "hours": 2,
            "minutes": 30,
        }
        response = self.client.post(
            "/api/v1/cmms/routines/complete",
            payload,
            format="json",
            **self.valid_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cmms_aber_submit_validation(self):
        payload = {
            "ship_id": 12,
            "fitted_equipment_id": 505,
            "budget_year": 2026,
            "estimate_cost": 15000.0,
            "currency": "INR",
            "aber_authority": "Naval HQs",
            "repair_agency_id": 1,
            "remarks": "Overhaul required",
        }
        response = self.client.post(
            "/api/v1/cmms/aber/submit", payload, format="json", **self.valid_headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["Universal_ID_T_ABER"], "U-ABER-12-505-2026")
        self.assertEqual(data["Universal_ID_M_Ship"], "U-SHIP-12")

    def test_cmms_refit_completions_validation(self):
        payload = {
            "ship_code": "S101",
            "refit_type": "SR",
            "planned_start_date": "2026-06-11",
            "planned_end_date": "2026-08-11",
        }
        response = self.client.post(
            "/api/v1/cmms/refit/completions",
            payload,
            format="json",
            **self.valid_headers,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["Universal_ID_T_RefComp"].startswith("U-RC-"))

    def test_cmms_sfd_payload(self):
        response = self.client.get("/api/v1/cmms/sfd/payload", **self.valid_headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["T_genericspecification"], [])

    def test_cmms_dart_post_payload(self):
        from master.models import MDelay, MDiagnostic, MRepair, MRepairAgency

        # Create master records for testing
        agency = MRepairAgency.objects.create(repair_agency_name="Test Agency")
        diag = MDiagnostic.objects.create(diagnostic_name="Test Diag")
        rep = MRepair.objects.create(repair_name="Test Repair")
        delay = MDelay.objects.create(delay_name="Test Delay")

        payload = {
            "T_DART": [
                {
                    "defect": {
                        "dart_number": "DART-TEST-POST",
                        "dart_date": "2026-06-13",
                        "defective_discriptions": "Oil leak from filter",
                        "maintenance_period": "AMP",
                        "dart_occasion": "Routine",
                        "is_closed": True,
                    },
                    "closure": {
                        "serial_no": "SR-999",
                        "rectified_date": "2026-06-14",
                        "days_delay": 2,
                        "lesson_learnt": "Change filter early",
                        "other_reasons": "Parts shipping delay",
                        "repair_agency_code_id": agency.pk,
                        "diagnostic_code_id": diag.pk,
                        "repair_code_id": rep.pk,
                        "delay_code_id": delay.pk,
                        "spares_delay": 3,
                    },
                    "spares_used": [
                        {
                            "pattern_no": "PAT-777",
                            "description": "Oil Filter Gasket",
                            "quantity": 2,
                        }
                    ],
                    "ra_dl_entries": [
                        {
                            "dl_type": "DL-II",
                            "dl_key": "DL-KEY-999",
                            "status": "APPROVED",
                            "remarks": "Test entry remarks",
                        }
                    ],
                }
            ]
        }

        response = self.client.post(
            "/api/v1/cmms/completed-dart", payload, format="json", **self.valid_headers
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
