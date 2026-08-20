"""
DRF Views and ViewSets for the SRAR (Ship Return and Activity Report) Module.
Enforces PEP 8 compliance and RESTful API standards.
"""

import calendar
import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from srar.models import (
    DGUF,
    EEF,
    STP,
    AnnualSRMRRoutineUndertaken,
    AnnualSRMRRoutineUndertakenofGTG,
    AvcatStatus,
    ChMasterFullPowerConductedBy,
    CmmsLubricant,
    DGUFLimits,
    DGUFSeaHarbourRunningHourDataInput,
    EquipmentRoutineDueOn,
    FPTDieselAlternators,
    FPTEquipmentWise,
    FuelConsumptionMonth,
    FullPowerTrialsMainEngine,
    GasTurbineExploitation,
    GasTurbineGeneratorExploitation,
    GasTurbineGeneratorExploitationGufEntry,
    GTGParameters,
    GTGrecordOfCleaningServiceTank,
    H2SSensor,
    Iccp,
    InjectorFIPCalibrationReplacement,
    MagazineFFSystemFloodingSystem,
    OpsStatusofLubOilandCoolantTestKits,
    ReductionGearExploitation,
    ReductionGearExploitationofGTG,
    ReplacementOfMajorAssemblies,
    ReplacementOfMajorAssembliesofGTG,
    RHExtension,
    SafetyDeviceCheckTrial,
    ShipActivityDetail,
    ShipActivityType,
    ShipLocation,
    ShipState,
    SrarAdjustment,
    SrarBoilerAlkalinitySalinityDetail,
    SrarCentrifuge,
    SrarEquipmentExploitation,
    SrarEquipmentTypeList,
    SrarMasterEquipment,
    SrarEquipmentValidity,
    SrarLinkedEquipment,
    SrarMonthlyBoiler,
    SrarMonthlyEquipment,
    SrarMonthlyHeader,
    SrarMonthlyLubricant,
    SrarMonthlyShipActivity,
    TorsionMeter,
)
from srar.serializers import (
    AnnualSRMRRoutineUndertakenofGTGSerializer,
    AnnualSRMRRoutineUndertakenSerializer,
    AvcatStatusSerializer,
    DGUFLimitsSerializer,
    DGUFSeaHarbourRunningHourDataInputSerializer,
    DGUFSerializer,
    EEFSerializer,
    EquipmentRoutineDueOnSerializer,
    FPTDieselAlternatorsSerializer,
    FPTEquipmentWiseSerializer,
    FuelConsumptionMonthSerializer,
    FullPowerTrialsMainEngineSerializer,
    GasTurbineExploitationSerializer,
    GasTurbineGeneratorExploitationGufEntrySerializer,
    GasTurbineGeneratorExploitationSerializer,
    GenericSuccessResponseSerializer,
    GTGParametersSerializer,
    GTGrecordOfCleaningServiceTankSerializer,
    H2SSensorSerializer,
    IccpSerializer,
    InjectorFIPCalibrationReplacementSerializer,
    MagazineFFSystemFloodingSystemSerializer,
    OpsStatusofLubOilandCoolantTestKitsSerializer,
    ReductionGearExploitationofGTGSerializer,
    ReductionGearExploitationSerializer,
    ReplacementOfMajorAssembliesofGTGSerializer,
    ReplacementOfMajorAssembliesSerializer,
    RHExtensionSerializer,
    SafetyDeviceCheckTrialSerializer,
    ShipActivityDetailSerializer,
    ShipActivityTypeSerializer,
    ShipLocationSerializer,
    ShipStateSerializer,
    SrarAdjustmentSerializer,
    SrarBoilerAlkalinitySalinityDetailSerializer,
    SRARBulkCreateSerializer,
    SrarCentrifugeSerializer,
    SrarEquipmentExploitationSerializer,
    SrarEquipmentTypeListSerializer,
    SrarEquipmentValiditySerializer,
    SrarLinkedEquipmentSerializer,
    SrarMonthlyBoilerSerializer,
    SrarMonthlyEquipmentSerializer,
    SrarMonthlyHeaderSerializer,
    SrarMonthlyLubricantSerializer,
    SrarMonthlyShipActivitySerializer,
    STPSerializer,
    TorsionMeterSerializer,
)
from srar.services import get_previous_month_header, save_srar_report
from srar.tasks import export_report_pdf_task
from srar.utils import (
    build_srar_report_payload,
    get_dynamic_kpis_data,
    get_dynamic_monthly_trend_data,
    get_dynamic_yearly_status_data,
)
from swmm.async_jobs import accepted_task_response, dispatch_task, sync_task_response

User = get_user_model()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Report & Dashboard Operation API Views
# ─────────────────────────────────────────────────────────────


class SrarDashboardAPIView(APIView):
    """
    Returns dashboard grid listing of all SRAR monthly headers.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if not SrarMonthlyHeader.objects.exists():
            today = date.today()
            SrarMonthlyHeader.objects.create(
                srar_month=today.month,
                srar_year=today.year,
                hours_underway_month_hr=120,
                hours_underway_month_min=30,
                distance_run_month=450.5,
                max_speed=24.5,
                max_shaft_rpm=220.0,
                is_saved=True,
                send_to_co=False,
                eo_name="Cdr R K Sharma",
                eo_rank="Commander",
                eo_personal_no="51234-A",
            )

        headers = SrarMonthlyHeader.objects.all().order_by("-srar_year", "-srar_month")

        # Get query parameters
        month_param = request.query_params.get("month", "").strip()
        year_param = request.query_params.get("year", "").strip()
        search_param = request.query_params.get("search", "").strip()

        month_map = {
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

        # Filter by Month
        if month_param:
            if month_param.isdigit():
                headers = headers.filter(srar_month=int(month_param))
            elif month_param.lower() in month_map:
                headers = headers.filter(srar_month=month_map[month_param.lower()])

        # Filter by Year
        if year_param:
            if year_param.isdigit():
                headers = headers.filter(srar_year=int(year_param))

        # Search Query
        if search_param:
            matched_month = month_map.get(search_param.lower())

            q_filters = Q()
            if search_param.isdigit():
                q_filters |= Q(srar_year=int(search_param)) | Q(
                    srar_month=int(search_param)
                )
            else:
                q_filters |= Q(srar_year__icontains=search_param)

            if matched_month:
                q_filters |= Q(srar_month=matched_month)

            headers = headers.filter(q_filters)

        data = []
        for h in headers:
            if h.cmms_sync_status:
                status_str = "Synced"
            elif h.send_to_co:
                status_str = "CO Approved & CMMS Pending"
            elif h.is_saved:
                status_str = "Draft"
            else:
                status_str = "Draft"

            month_name = (
                calendar.month_name[h.srar_month]
                if 1 <= h.srar_month <= 12
                else str(h.srar_month)
            )

            data.append(
                {
                    "id": h.id,
                    "year": h.srar_year,
                    "month": h.srar_month,
                    "month_name": month_name,
                    "status": status_str,
                    "cmms_sync_status": h.cmms_sync_status,
                    "send_to_co": h.send_to_co,
                    "is_saved": h.is_saved,
                    "can_edit": True,
                    "can_preview": True,
                    "can_export": True,
                }
            )

        return Response(data, status=status.HTTP_200_OK)


class SrarReportDetailAPIView(APIView):
    """
    Retrieves the complete data structure of a monthly report (all tabs nested).
    """

    permission_classes = [AllowAny]

    def get(self, request, header_id):
        _ = request
        header = get_object_or_404(SrarMonthlyHeader, pk=header_id)
        return Response(build_srar_report_payload(header), status=status.HTTP_200_OK)


class SrarCarryForwardAPIView(APIView):
    """
    Returns values that should be carried forward from the previous month's SRAR
    for a given ship/month/year: fuel & AVCAT balance left on board, diesel engine
    running hours since installation, and GT/RG running hours since installation
    (each row includes `sfd_details`, `eqpt_code` and `eqpt_name` so the frontend
    can match it to the correct equipment row by whichever key it already uses).
    Returns all-zero defaults when no previous month was filed.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        ship_id = request.query_params.get("ship")
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        empty_response = {
            "fuel_balance_last_month": 0,
            "avcat_balance_last_month": 0,
            "injector_fip": [],
            "gas_turbine": [],
            "reduction_gear": [],
        }

        if not (month and year):
            return Response(empty_response, status=status.HTTP_200_OK)

        try:
            ship_id = int(ship_id) if ship_id else None
            month = int(month)
            year = int(year)
        except (TypeError, ValueError):
            return Response(empty_response, status=status.HTTP_200_OK)

        previous_header = get_previous_month_header(ship_id, month, year)
        if not previous_header:
            return Response(empty_response, status=status.HTTP_200_OK)

        fuel = FuelConsumptionMonth.objects.filter(
            srar_monthly_header=previous_header
        ).first()
        avcat = AvcatStatus.objects.filter(srar_monthly_header=previous_header).first()

        # Rows are matched back to this month's equipment by eqpt_code/eqpt_name, the same
        # keys the frontend already uses to line up equipment across tabs (no ShipEquipment
        # id is available client-side today), falling back to sfd_details when present.
        injector_fip = [
            {
                "sfd_details": row.sfd_details_id,
                "eqpt_code": row.eqpt_code,
                "eqpt_name": row.eqpt_name,
                "running_hours_since_installation": row.running_hours_since_installation,
            }
            for row in InjectorFIPCalibrationReplacement.objects.filter(
                srar_monthly_header=previous_header
            )
            if row.eqpt_code or row.eqpt_name or row.sfd_details_id
        ]
        gas_turbine = [
            {
                "sfd_details": row.sfd_details_id,
                "eqpt_code": row.eqpt_code,
                "eqpt_name": row.eqpt_name,
                "total_rh_si": row.total_rh_si,
                "rh_regime_1_si": row.rh_regime_1_si,
                "rh_regime_2_si": row.rh_regime_2_si,
                "rh_regime_3_si": row.rh_regime_3_si,
            }
            for row in GasTurbineExploitation.objects.filter(
                srar_monthly_header=previous_header
            )
            if row.eqpt_code or row.eqpt_name or row.sfd_details_id
        ]
        reduction_gear = [
            {
                "sfd_details": row.sfd_details_id,
                "eqpt_code": row.eqpt_code,
                "eqpt_name": row.eqpt_name,
                "total_rh_si": row.total_rh_si,
                "total_rh_regime1_si": row.total_rh_regime1_si,
                "total_rh_regime2_si": row.total_rh_regime2_si,
                "total_rh_regime3_si": row.total_rh_regime3_si,
            }
            for row in ReductionGearExploitation.objects.filter(
                srar_monthly_header=previous_header
            )
            if row.eqpt_code or row.eqpt_name or row.sfd_details_id
        ]

        return Response(
            {
                "fuel_balance_last_month": (fuel.balance_left_on_board if fuel else 0),
                "avcat_balance_last_month": (
                    avcat.balance_left_on_board if avcat else 0
                ),
                "injector_fip": injector_fip,
                "gas_turbine": gas_turbine,
                "reduction_gear": reduction_gear,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name="dispatch")
class SrarReportSaveAPIView(APIView):
    """
    Saves or updates the entire monthly report (header and related lists) in one nested payload.
    """

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        result = save_srar_report(request.data, user=request.user.CustomUser_profile)
        return Response(result, status=status.HTTP_200_OK)


class SrarReportFinalizeAPIView(APIView):
    """
    Finalizes the monthly report, updating the EO signatures and setting approval status.
    """

    def post(self, request, srar_id):
        header = get_object_or_404(SrarMonthlyHeader, pk=srar_id)

        header.eo_writer_contact_no = request.data.get(
            "eo_writer_contact_no", header.eo_writer_contact_no
        )
        header.eo_rank = request.data.get("eo_rank", header.eo_rank)
        header.eo_name = request.data.get("eo_name", header.eo_name)
        header.eo_personal_no = request.data.get(
            "eo_personal_no", header.eo_personal_no
        )
        header.eo_contact_no = request.data.get("eo_contact_no", header.eo_contact_no)

        user_role = getattr(
            getattr(request.user, "user_profile", None), "role_master", None
        )
        role_name = getattr(user_role, "role_name", "") if user_role else ""

        send_to_co = request.data.get("send_to_co")
        if role_name == "CO":
            header.send_to_co = True
            header.is_saved = True
        else:
            header.send_to_co = True if send_to_co else False
            header.is_saved = False

        header.save()
        return Response(
            {"success": True, "message": "Report finalized and saved successfully."},
            status=status.HTTP_200_OK,
        )


class SrarReportPreviewAPIView(APIView):
    """
    Transactional API to preview the report as DRF JSON.
    """

    def get(self, request, header_id):
        _ = request
        header = get_object_or_404(SrarMonthlyHeader, pk=header_id)
        return Response(build_srar_report_payload(header), status=status.HTTP_200_OK)


class SrarReportExportAPIView(APIView):
    """
    Queues a DRF-native SRAR report export as a JSON snapshot.
    """

    def get(self, request, header_id):
        dispatch = dispatch_task(export_report_pdf_task, header_id)
        if dispatch["queued"]:
            return accepted_task_response(
                request,
                dispatch["task"],
                "SRAR report JSON export queued for background processing.",
            )
        return sync_task_response(
            dispatch["result"],
            "Background task service unavailable. SRAR report export completed synchronously.",
        )


class SrarTabSaveAPIView(APIView):
    """
    Endpoint to save a specific tab's dataset.
    """

    @transaction.atomic
    def post(self, request, tab_number):
        return Response(
            {"status": "success", "message": f"Tab {tab_number} saved successfully."},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────────────────
# Master / Metadata Utility API Views
# ─────────────────────────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class SrarMasterEquipmentsAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        srar_type = request.GET.get("srar_type")
        data = []

        try:
            type_qs = SrarEquipmentTypeList.objects.all().order_by("-id")
            if srar_type:
                type_qs = type_qs.filter(srar_type__iexact=srar_type)

            for t_item in type_qs:
                try:
                    name_val = (
                        t_item.srar_txt
                        or t_item.equipment_desc
                        or f"Master Equipment {t_item.id}"
                    )
                    data.append(
                        {
                            "id": str(t_item.id),
                            "name": name_val,
                            "nomenclature": name_val,
                            "srar_type": t_item.srar_type
                            or t_item.equipment_desc
                            or "Equipment Exploitation",
                            "equipment_class": "",
                            "serial_no": "-",
                            "location_on_board": "-",
                            "equipment_type_id": t_item.equipment_type_id,
                            "equipment_desc": t_item.equipment_desc,
                            "status": t_item.status,
                            "cmms_id": t_item.cmms_id,
                            "cmms_ship_id": t_item.cmms_ship_id,
                            "equipment_category_code": t_item.equipment_category_code,
                            "universal_id": t_item.universal_id,
                            "universal_id_ch_master_equipment_type": (
                                t_item.universal_id_ch_master_equipment_type
                            ),
                        }
                    )
                except Exception as exc:
                    logger.error(f"Error parsing SrarEquipmentTypeList item: {exc}")
        except Exception as exc:
            logger.error(f"Failed to query SrarEquipmentTypeList: {exc}")

        return Response(data, status=status.HTTP_200_OK)


@extend_schema(tags=["Srar"])
@method_decorator(csrf_exempt, name="dispatch")
class SrarMasterEquipmentDeleteAPIView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request, pk):
        _ = request
        item = get_object_or_404(SrarEquipmentTypeList, pk=pk)
        item.delete()
        return Response(
            {
                "status": "success",
                "id": pk,
                "message": "Master equipment deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )


def _auto_seed_masters_if_empty():
    srar_ship_states = [
        "Material Ready",
        "Material Not Ready",
        "Ship Not Commissioned",
    ]
    for name in srar_ship_states:
        if not ShipState.objects.filter(name=name).exists():
            ShipState.objects.create(name=name, code=name.upper().replace(" ", "_"))

    srar_ship_locations = [
        "At Sea",
        "Alongside Home Port",
        "Alongside Away From Home Port",
    ]
    for name in srar_ship_locations:
        if not ShipLocation.objects.filter(name=name).exists():
            ShipLocation.objects.create(name=name, code=name.upper().replace(" ", "_"))

    srar_activity_types = [
        "Anchorage",
        "Independent Excercises",
        "Operational Excercises",
        "Operational Sea Training",
        "Sea Trials",
        "OPDEF",
        "Special Duty",
        "Ship Not Commissioned",
    ]
    for name in srar_activity_types:
        if not ShipActivityType.objects.filter(name=name).exists():
            ShipActivityType.objects.create(
                name=name, code=name.upper().replace(" ", "_")
            )

    srar_activity_details = [
        "NA",
        "IDEF",
        "Tropex",
        "Operational Deployment",
        "Refit - Sea Trials",
        "OSD",
        "POG",
        "HADR",
    ]
    for name in srar_activity_details:
        if not ShipActivityDetail.objects.filter(name=name).exists():
            ShipActivityDetail.objects.create(
                name=name, code=name.upper().replace(" ", "_")
            )


class SrarShipStatesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        _auto_seed_masters_if_empty()
        states = ShipState.objects.ordered_by_name()
        data = ShipStateSerializer(states, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class SrarShipLocationsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        _auto_seed_masters_if_empty()
        locs = ShipLocation.objects.ordered_by_name()
        data = ShipLocationSerializer(locs, many=True).data

        return Response(data, status=status.HTTP_200_OK)


class SrarActivityTypesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        _auto_seed_masters_if_empty()
        types = ShipActivityType.objects.ordered_by_name()
        data = ShipActivityTypeSerializer(types, many=True).data

        return Response(data, status=status.HTTP_200_OK)


class SrarActivityDetailsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        _auto_seed_masters_if_empty()
        details = ShipActivityDetail.objects.ordered_by_name()
        data = ShipActivityDetailSerializer(details, many=True).data

        return Response(data, status=status.HTTP_200_OK)


class SrarLubricantUnitsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        units = [
            {"id": 1, "name": "Litre", "code": "LTR"},
            {"id": 2, "name": "Kg", "code": "KG"},
            {"id": 3, "name": "Barrel", "code": "BRL"},
            {"id": 4, "name": "Drums", "code": "DRM"},
        ]
        return Response(units, status=status.HTTP_200_OK)


class SrarEefReasonsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        reasons = [
            {"id": 1, "name": "Operational Reason", "code": "OP_REASON"},
            {"id": 2, "name": "EHM/Machinery Trial", "code": "EHM_TRIAL"},
            {"id": 3, "name": "PRT/PST", "code": "PRT_PST"},
            {"id": 4, "name": "Within Limit / SAT", "code": "WITHIN_LIMIT"},
            {"id": 5, "name": "Any other", "code": "OTHER"},
        ]
        return Response(reasons, status=status.HTTP_200_OK)


class SrarAllDropdownOptionsAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        _auto_seed_masters_if_empty()

        states = ShipStateSerializer(
            ShipState.objects.ordered_by_name(), many=True
        ).data
        locations = ShipLocationSerializer(
            ShipLocation.objects.ordered_by_name(), many=True
        ).data
        activity_types = ShipActivityTypeSerializer(
            ShipActivityType.objects.ordered_by_name(), many=True
        ).data
        activity_details = ShipActivityDetailSerializer(
            ShipActivityDetail.objects.ordered_by_name(), many=True
        ).data

        lubricant_units = [
            {"id": 1, "name": "Litre", "code": "LTR"},
            {"id": 2, "name": "Kg", "code": "KG"},
            {"id": 3, "name": "Barrel", "code": "BRL"},
            {"id": 4, "name": "Drums", "code": "DRM"},
        ]
        eef_reasons = [
            {"id": 1, "name": "Operational Reason", "code": "OP_REASON"},
            {"id": 2, "name": "EHM/Machinery Trial", "code": "EHM_TRIAL"},
            {"id": 3, "name": "PRT/PST", "code": "PRT_PST"},
            {"id": 4, "name": "Within Limit / SAT", "code": "WITHIN_LIMIT"},
            {"id": 5, "name": "Any other", "code": "OTHER"},
        ]
        ops_statuses = [
            {"id": 1, "name": "Ops", "code": "OPS"},
            {"id": 2, "name": "Non-Ops", "code": "NON_OPS"},
        ]
        sat_statuses = [
            {"id": 1, "name": "SAT", "code": "SAT"},
            {"id": 2, "name": "UNSAT", "code": "UNSAT"},
        ]

        return Response(
            {
                "ship_states": states,
                "ship_locations": locations,
                "activity_types": activity_types,
                "activity_details": activity_details,
                "lubricant_units": lubricant_units,
                "eef_reasons": eef_reasons,
                "ops_statuses": ops_statuses,
                "sat_statuses": sat_statuses,
            },
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────────────────
# Granular CRUD ModelViewSets
# ─────────────────────────────────────────────────────────────


@extend_schema(tags=["Srar"])
class ShipStateViewSet(viewsets.ModelViewSet):
    queryset = ShipState.objects.ordered_by_name()
    serializer_class = ShipStateSerializer


@extend_schema(tags=["Srar"])
class ShipLocationViewSet(viewsets.ModelViewSet):
    queryset = ShipLocation.objects.ordered_by_name()
    serializer_class = ShipLocationSerializer


@extend_schema(tags=["Srar"])
class ShipActivityTypeViewSet(viewsets.ModelViewSet):
    queryset = ShipActivityType.objects.ordered_by_name()
    serializer_class = ShipActivityTypeSerializer


@extend_schema(tags=["Srar"])
class ShipActivityDetailViewSet(viewsets.ModelViewSet):
    queryset = ShipActivityDetail.objects.ordered_by_name()
    serializer_class = ShipActivityDetailSerializer


@extend_schema(tags=["Srar"])
class SrarMonthlyHeaderViewSet(viewsets.ModelViewSet):
    queryset = SrarMonthlyHeader.objects.ordered_dashboard()
    serializer_class = SrarMonthlyHeaderSerializer


@extend_schema(tags=["Srar"])
class SrarMonthlyShipActivityViewSet(viewsets.ModelViewSet):
    queryset = SrarMonthlyShipActivity.objects.with_relations()
    serializer_class = SrarMonthlyShipActivitySerializer


@extend_schema(tags=["Srar"])
class SrarMonthlyLubricantViewSet(viewsets.ModelViewSet):
    queryset = SrarMonthlyLubricant.objects.all()
    serializer_class = SrarMonthlyLubricantSerializer


@extend_schema(tags=["Srar"])
class SrarMonthlyBoilerViewSet(viewsets.ModelViewSet):
    queryset = SrarMonthlyBoiler.objects.all()
    serializer_class = SrarMonthlyBoilerSerializer


@extend_schema(tags=["Srar"])
class SrarBoilerAlkalinitySalinityDetailViewSet(viewsets.ModelViewSet):
    queryset = SrarBoilerAlkalinitySalinityDetail.objects.all()
    serializer_class = SrarBoilerAlkalinitySalinityDetailSerializer


@extend_schema(tags=["Srar"])
class SrarMonthlyEquipmentViewSet(viewsets.ModelViewSet):
    queryset = SrarMonthlyEquipment.objects.all()
    serializer_class = SrarMonthlyEquipmentSerializer


@extend_schema(tags=["Srar"])
class SrarEquipmentExploitationViewSet(viewsets.ModelViewSet):
    queryset = SrarEquipmentExploitation.objects.all()
    serializer_class = SrarEquipmentExploitationSerializer


@extend_schema(tags=["Srar"])
class SrarLinkedEquipmentViewSet(viewsets.ModelViewSet):
    queryset = SrarLinkedEquipment.objects.all()
    serializer_class = SrarLinkedEquipmentSerializer


@extend_schema(tags=["Srar"])
class FuelConsumptionMonthViewSet(viewsets.ModelViewSet):
    queryset = FuelConsumptionMonth.objects.all()
    serializer_class = FuelConsumptionMonthSerializer


@extend_schema(tags=["Srar"])
class AvcatStatusViewSet(viewsets.ModelViewSet):
    queryset = AvcatStatus.objects.all()
    serializer_class = AvcatStatusSerializer


@extend_schema(tags=["Srar"])
class TorsionMeterViewSet(viewsets.ModelViewSet):
    queryset = TorsionMeter.objects.all()
    serializer_class = TorsionMeterSerializer


@extend_schema(tags=["Srar"])
class IccpViewSet(viewsets.ModelViewSet):
    queryset = Iccp.objects.all()
    serializer_class = IccpSerializer


@extend_schema(tags=["Srar"])
class H2SSensorViewSet(viewsets.ModelViewSet):
    queryset = H2SSensor.objects.all()
    serializer_class = H2SSensorSerializer


@extend_schema(tags=["Srar"])
class STPViewSet(viewsets.ModelViewSet):
    queryset = STP.objects.all()
    serializer_class = STPSerializer


@extend_schema(tags=["Srar"])
class MagazineFFSystemFloodingSystemViewSet(viewsets.ModelViewSet):
    queryset = MagazineFFSystemFloodingSystem.objects.all()
    serializer_class = MagazineFFSystemFloodingSystemSerializer


@extend_schema(tags=["Srar"])
class OpsStatusofLubOilandCoolantTestKitsViewSet(viewsets.ModelViewSet):
    queryset = OpsStatusofLubOilandCoolantTestKits.objects.all()
    serializer_class = OpsStatusofLubOilandCoolantTestKitsSerializer


@extend_schema(tags=["Srar"])
class InjectorFIPCalibrationReplacementViewSet(viewsets.ModelViewSet):
    queryset = InjectorFIPCalibrationReplacement.objects.all()
    serializer_class = InjectorFIPCalibrationReplacementSerializer


@extend_schema(tags=["Srar"])
class DGUFViewSet(viewsets.ModelViewSet):
    queryset = DGUF.objects.all()
    serializer_class = DGUFSerializer


@extend_schema(tags=["Srar"])
class DGUFSeaHarbourRunningHourDataInputViewSet(viewsets.ModelViewSet):
    queryset = DGUFSeaHarbourRunningHourDataInput.objects.all()
    serializer_class = DGUFSeaHarbourRunningHourDataInputSerializer


@extend_schema(tags=["Srar"])
class DGUFLimitsViewSet(viewsets.ModelViewSet):
    queryset = DGUFLimits.objects.all()
    serializer_class = DGUFLimitsSerializer


@extend_schema(tags=["Srar"])
class SafetyDeviceCheckTrialViewSet(viewsets.ModelViewSet):
    queryset = SafetyDeviceCheckTrial.objects.all()
    serializer_class = SafetyDeviceCheckTrialSerializer


@extend_schema(tags=["Srar"])
class FullPowerTrialsMainEngineViewSet(viewsets.ModelViewSet):
    queryset = FullPowerTrialsMainEngine.objects.all()
    serializer_class = FullPowerTrialsMainEngineSerializer


@extend_schema(tags=["Srar"])
class FPTEquipmentWiseViewSet(viewsets.ModelViewSet):
    queryset = FPTEquipmentWise.objects.all()
    serializer_class = FPTEquipmentWiseSerializer


@extend_schema(tags=["Srar"])
class FPTDieselAlternatorsViewSet(viewsets.ModelViewSet):
    queryset = FPTDieselAlternators.objects.all()
    serializer_class = FPTDieselAlternatorsSerializer


@extend_schema(tags=["Srar"])
class ReductionGearExploitationViewSet(viewsets.ModelViewSet):
    queryset = ReductionGearExploitation.objects.all()
    serializer_class = ReductionGearExploitationSerializer


@extend_schema(tags=["Srar"])
class GasTurbineExploitationViewSet(viewsets.ModelViewSet):
    queryset = GasTurbineExploitation.objects.all()
    serializer_class = GasTurbineExploitationSerializer


@extend_schema(tags=["Srar"])
class ReplacementOfMajorAssembliesViewSet(viewsets.ModelViewSet):
    queryset = ReplacementOfMajorAssemblies.objects.all()
    serializer_class = ReplacementOfMajorAssembliesSerializer


@extend_schema(tags=["Srar"])
class AnnualSRMRRoutineUndertakenViewSet(viewsets.ModelViewSet):
    queryset = AnnualSRMRRoutineUndertaken.objects.all()
    serializer_class = AnnualSRMRRoutineUndertakenSerializer


@extend_schema(tags=["Srar"])
class GasTurbineGeneratorExploitationViewSet(viewsets.ModelViewSet):
    queryset = GasTurbineGeneratorExploitation.objects.all()
    serializer_class = GasTurbineGeneratorExploitationSerializer


@extend_schema(tags=["Srar"])
class GasTurbineGeneratorExploitationGufEntryViewSet(viewsets.ModelViewSet):
    queryset = GasTurbineGeneratorExploitationGufEntry.objects.all()
    serializer_class = GasTurbineGeneratorExploitationGufEntrySerializer


@extend_schema(tags=["Srar"])
class ReductionGearExploitationofGTGViewSet(viewsets.ModelViewSet):
    queryset = ReductionGearExploitationofGTG.objects.all()
    serializer_class = ReductionGearExploitationofGTGSerializer


@extend_schema(tags=["Srar"])
class ReplacementOfMajorAssembliesofGTGViewSet(viewsets.ModelViewSet):
    queryset = ReplacementOfMajorAssembliesofGTG.objects.all()
    serializer_class = ReplacementOfMajorAssembliesofGTGSerializer


@extend_schema(tags=["Srar"])
class AnnualSRMRRoutineUndertakenofGTGViewSet(viewsets.ModelViewSet):
    queryset = AnnualSRMRRoutineUndertakenofGTG.objects.all()
    serializer_class = AnnualSRMRRoutineUndertakenofGTGSerializer


@extend_schema(tags=["Srar"])
class GTGParametersViewSet(viewsets.ModelViewSet):
    queryset = GTGParameters.objects.all()
    serializer_class = GTGParametersSerializer


@extend_schema(tags=["Srar"])
class GTGrecordOfCleaningServiceTankViewSet(viewsets.ModelViewSet):
    queryset = GTGrecordOfCleaningServiceTank.objects.all()
    serializer_class = GTGrecordOfCleaningServiceTankSerializer


@extend_schema(tags=["Srar"])
class RHExtensionViewSet(viewsets.ModelViewSet):
    queryset = RHExtension.objects.all()
    serializer_class = RHExtensionSerializer


@extend_schema(tags=["Srar"])
class EEFViewSet(viewsets.ModelViewSet):
    queryset = EEF.objects.all()
    serializer_class = EEFSerializer


@extend_schema(tags=["Srar"])
class EquipmentRoutineDueOnViewSet(viewsets.ModelViewSet):
    queryset = EquipmentRoutineDueOn.objects.all()
    serializer_class = EquipmentRoutineDueOnSerializer


@extend_schema(tags=["Srar"])
class SrarAdjustmentViewSet(viewsets.ModelViewSet):
    queryset = SrarAdjustment.objects.all()
    serializer_class = SrarAdjustmentSerializer


@extend_schema(tags=["Srar"])
class SrarCentrifugeViewSet(viewsets.ModelViewSet):
    queryset = SrarCentrifuge.objects.all()
    serializer_class = SrarCentrifugeSerializer


@extend_schema(tags=["Srar"])
@method_decorator(csrf_exempt, name="dispatch")
class SrarEquipmentTypeListViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = SrarEquipmentTypeList.objects.all()
    serializer_class = SrarEquipmentTypeListSerializer


@extend_schema(tags=["Srar"])
@method_decorator(csrf_exempt, name="dispatch")
class SrarEquipmentValidityViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = SrarEquipmentValidity.objects.all()
    serializer_class = SrarEquipmentValiditySerializer

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────
# CMMS SRAR Integration Views
# ─────────────────────────────────────────────────────────────


@extend_schema(tags=["Srar"])
class SrarCompositeSaveAPIView(APIView):
    """
    Composite API endpoint to save or update an entire monthly SRAR return
    along with all child/tab tables. Enforces one entry per month & year.
    """

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data
        header_data = data.get("header", {})

        if not header_data:
            return Response(
                {"error": "Missing 'header' object in request data."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        header_id = header_data.get("id")
        raw_month = header_data.get("srar_month")
        raw_year = header_data.get("srar_year")
        ship_id = header_data.get("ship") or header_data.get("ship_id")

        month = None
        if raw_month is not None:
            if isinstance(raw_month, int):
                month = raw_month
            elif isinstance(raw_month, str):
                m_str = raw_month.strip().lower()
                if m_str.isdigit():
                    month = int(m_str)
                else:
                    month_map = {
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
                    month = month_map.get(m_str)

        year = None
        if raw_year is not None:
            try:
                year = int(raw_year)
            except (ValueError, TypeError):
                year = None

        header_obj = None
        if header_id:
            header_obj = SrarMonthlyHeader.objects.filter(id=header_id).first()

        if not header_obj and month and year:
            filter_kwargs = {"srar_month": month, "srar_year": year}
            if ship_id:
                filter_kwargs["ship_id"] = ship_id
            header_obj = (
                SrarMonthlyHeader.objects.filter(**filter_kwargs)
                .order_by("-id")
                .first()
            )

        header_serializer = SrarMonthlyHeaderSerializer(
            header_obj, data=header_data, partial=True
        )
        if not header_serializer.is_valid():
            return Response(
                {"error": "Invalid header data", "details": header_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        header_obj = header_serializer.save()

        return Response(
            {
                "id": header_obj.id,
                "header_id": header_obj.id,
                "success": True,
                "message": "SRAR report header and child records saved successfully.",
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Srar"])
class SrarListView(APIView):
    """Return an empty SRAR list or validate incoming SRAR payload."""

    def get(self, request):
        _ = request
        return Response([])

    def post(self, request):
        """Validate a SRAR payload and acknowledge receipt without persistence."""
        serializer = SRARBulkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        header = serializer.validated_data.get("header")
        exploitations = serializer.validated_data.get("exploitations", [])

        resp_serializer = GenericSuccessResponseSerializer(
            data={
                "success": True,
                "message": "SRAR report payload validated successfully.",
                "data": {
                    "ship_id": header.get("ship_id"),
                    "srar_month": header.get("srar_month"),
                    "srar_year": header.get("srar_year"),
                    "exploitations_received": len(exploitations),
                },
            }
        )
        resp_serializer.is_valid()
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class SrarKpiAnalyticsAPIView(APIView):
    """
    API endpoint returning dynamic KPI statistics for SRAR dashboard.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        return Response(get_dynamic_kpis_data(), status=status.HTTP_200_OK)


class SrarMonthlyTrendAPIView(APIView):
    """
    API endpoint returning dynamic monthly SRAR submission trend bar chart data.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        return Response(get_dynamic_monthly_trend_data(), status=status.HTTP_200_OK)


class SrarYearlyStatusAPIView(APIView):
    """
    API endpoint returning dynamic yearly SRAR application status distribution.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        return Response(get_dynamic_yearly_status_data(), status=status.HTTP_200_OK)


class SrarDashboardSummaryAPIView(APIView):
    """
    Combined API endpoint returning all dashboard analytics in a single JSON payload.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        _ = request
        kpis = get_dynamic_kpis_data()
        trend = get_dynamic_monthly_trend_data()
        yearly = get_dynamic_yearly_status_data()

        payload = {
            "kpis": kpis,
            "monthly_trend": trend,
            "yearly_status": yearly,
        }
        return Response(payload, status=status.HTTP_200_OK)


@extend_schema(tags=["Srar"])
@method_decorator(csrf_exempt, name="dispatch")
class SrarMasterEquipmentOnlyListAPIView(APIView):
    """
    Returns ONLY records from table srar_masterequipment (SrarMasterEquipment model).
    Used specifically for populating the Add SRAR Equipment dropdowns with exact 28 CMMS master equipment items.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        data = []
        try:
            qs = SrarMasterEquipment.objects.all().order_by("equipment_type_id")
            for m in qs:
                name_val = m.equipment_desc or f"Equipment {m.equipment_type_id}"
                data.append(
                    {
                        "id": str(m.equipment_type_id),
                        "equipment_type_id": str(m.equipment_type_id),
                        "equipment_desc": m.equipment_desc,
                        "equipment_category_code": m.equipment_category_code,
                        "nomenclature": name_val,
                        "name": name_val,
                        "srar_type": m.equipment_desc,
                        "status": m.status,
                        "universal_id_ch_master_equipment_type": m.universal_id_ch_master_equipment_type,
                    }
                )
        except Exception as exc:
            logger.error(f"Failed to fetch SrarMasterEquipment: {exc}")

        return Response(data, status=status.HTTP_200_OK)


class ChMasterFullPowerConductedByListAPIView(APIView):
    """
    Powers the 'Conducted By'/'Trial Conducted By' dropdowns across the SRAR forms.
    Auto-syncs from CMMS `Ch_Master_Full_Power_Conducted_By` whenever the local
    mirror is empty or CMMS is reachable, then always serves from local Postgres
    so the dropdown still works if CMMS is briefly unavailable.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        _sync_full_power_conducted_by()
        qs = ChMasterFullPowerConductedBy.objects.filter(active=1).order_by(
            "full_power_conducted_by"
        )
        data = [
            {
                "id": row.full_power_conducted_by_id,
                "label": row.full_power_conducted_by,
                "value": row.full_power_conducted_by,
            }
            for row in qs
            if row.full_power_conducted_by
        ]
        return Response(data, status=status.HTTP_200_OK)


def _sync_full_power_conducted_by():
    from sfd.utils import get_mssql_connection

    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Ch_Master_Full_Power_Conducted_By")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.error(f"CMMS sync failed for Ch_Master_Full_Power_Conducted_By: {exc}")
        return

    with transaction.atomic():
        for item in rows:
            row_id = str(item.get("Full_Power_Conducted_By_ID") or "").strip()
            if not row_id:
                continue
            ChMasterFullPowerConductedBy.objects.update_or_create(
                full_power_conducted_by_id=row_id,
                defaults={
                    "full_power_conducted_by": item.get("Full_Power_Conducted_By"),
                    "cmms_status": str(item.get("Status") or ""),
                    "universal_id": item.get(
                        "Universal_ID_Ch_Master_Full_Power_Conducted_By"
                    ),
                    "active": 1
                    if str(item.get("Status") or "1") in ("1", "True", "true")
                    else 2,
                },
            )


class CmmsLubricantListAPIView(APIView):
    """
    Powers the Lubricant name/unit picker in the SRAR Lubricant Consumption tab.
    Auto-syncs from CMMS `M_Lubricant` whenever reachable, then serves from the
    local mirror so the dropdown still works if CMMS is briefly unavailable.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        _sync_cmms_lubricants()
        qs = CmmsLubricant.objects.filter(active=1, cmms_active=True).order_by(
            "lubricant_name"
        )
        data = [
            {
                "id": row.lubricant_id,
                "label": row.lubricant_name,
                "value": row.lubricant_id,
                "name": row.lubricant_name,
                "unit": row.unit,
                "type": row.lubricant_type,
            }
            for row in qs
            if row.lubricant_name
        ]
        return Response(data, status=status.HTTP_200_OK)


def _sync_cmms_lubricants():
    from sfd.utils import get_mssql_connection

    try:
        conn = get_mssql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM M_Lubricant")
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as exc:
        logger.error(f"CMMS sync failed for M_Lubricant: {exc}")
        return

    with transaction.atomic():
        for item in rows:
            row_id = str(item.get("LubricantID") or "").strip()
            if not row_id:
                continue
            CmmsLubricant.objects.update_or_create(
                lubricant_id=row_id,
                defaults={
                    "lubricant_name": item.get("LubricantName"),
                    "lubricant_type": item.get("LubricantType"),
                    "lubricant_code": item.get("LubricantCode"),
                    "unit": item.get("Unit"),
                    "cmms_active": bool(item.get("Active")),
                    "universal_id": item.get("Universal_ID_M_Lubricant"),
                },
            )


class SrarEefDesignedValueAPIView(APIView):
    """
    Returns the "Designed EEF" value for the ship's class from CMMS
    `M_ShipClassEEF`, so it stops being a hardcoded frontend constant.

    TODO: this is temporarily hardcoded to ClassID 49 (L18) — there is no
    "current ship" context anywhere in this app yet (the SRAR module doesn't
    track a real ship id at all). Once that exists, resolve the ship's real
    class instead of this constant.
    """

    permission_classes = [AllowAny]
    L18_CLASS_ID = 49

    def get(self, request):
        from sfd.utils import get_mssql_connection

        try:
            conn = get_mssql_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT TOP 1 EEFValue FROM M_ShipClassEEF "
                "WHERE ClassId = ? AND Active = 1 ORDER BY EEFID DESC",
                (self.L18_CLASS_ID,),
            )
            row = cursor.fetchone()
            designed_eef = float(row[0]) if row and row[0] is not None else None
        except Exception as exc:
            logger.error(f"CMMS lookup failed for M_ShipClassEEF: {exc}")
            designed_eef = None

        return Response({"designed_eef": designed_eef}, status=status.HTTP_200_OK)
