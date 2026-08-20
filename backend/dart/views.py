import csv
import io

from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from master.models import MReason, MRequiredAssistance, MSeverity
from rest_framework import generics, status, views, viewsets
from rest_framework.response import Response

from . import swagger
from .filters import (
    ClosedDartsReportFilter,
    DartsReportFilter,
    GuaranteeMonitoringReportFilter,
    RaStatusReportFilter,
    ServiceRequiredReportFilter,
    SparesConsumedReportFilter,
)
from .models import (
    CertificateTypeMaster,
    InitiateDart,
    RepairAgencyMaster,
    ServiceMaster,
    ShipRemarksMaster,
)
from .report_registry import apply_filterset, get_report_definition
from .serializers import (
    AssistanceMasterListSerializer,
    CertificateTypeMasterListSerializer,
    ClosedDartsReportSerializer,
    DartDashboardSerializer,
    DartsReportSerializer,
    GuaranteeMonitoringReportSerializer,
    RaStatusReportSerializer,
    ReasonMasterListSerializer,
    RepairAgencyMasterListSerializer,
    ServiceMasterListSerializer,
    ServiceRequiredReportSerializer,
    SeverityMasterListSerializer,
    ShipRemarksMasterListSerializer,
    SparesConsumedReportSerializer,
)
from .services import DartDashboardService


# Config related views
##############################################################################
@swagger.REPAIRAGENCYMASTERLISTAPIVIEW_SCHEMA
class RepairAgencyMasterListAPIView(generics.ListAPIView):
    queryset = RepairAgencyMaster.objects.all().order_by("repair_agency_name")
    serializer_class = RepairAgencyMasterListSerializer


@swagger.ASSISTANCEMASTERLISTAPIVIEW_SCHEMA
class AssistanceMasterListAPIView(generics.ListAPIView):
    queryset = MRequiredAssistance.objects.filter(active=True).order_by(
        "required_assistance_id"
    )
    serializer_class = AssistanceMasterListSerializer


@swagger.REASONMASTERLISTAPIVIEW_SCHEMA
class ReasonMasterListAPIView(generics.ListAPIView):
    queryset = MReason.objects.filter(active=True).order_by("reason_code")
    serializer_class = ReasonMasterListSerializer


@swagger.SEVERITYMASTERLISTAPIVIEW_SCHEMA
class SeverityMasterListAPIView(generics.ListAPIView):
    queryset = MSeverity.objects.filter(active=True).order_by("severity_code")
    serializer_class = SeverityMasterListSerializer


@swagger.SERVICESMASTERLISTAPIVIEW_SCHEMA
class ServicesMasterListAPIView(generics.ListAPIView):
    queryset = ServiceMaster.objects.filter(active=1).order_by("service")
    serializer_class = ServiceMasterListSerializer


@swagger.CERTIFICATETYPEMASTERLISTAPIVIEW_SCHEMA
class CertificateTypeMasterListAPIView(generics.ListAPIView):
    queryset = CertificateTypeMaster.objects.filter(active=1).order_by("certificate")
    serializer_class = CertificateTypeMasterListSerializer


@swagger.SHIPREMARKSMASTERLISTAPIVIEW_SCHEMA
class ShipRemarksMasterListAPIView(generics.ListAPIView):
    queryset = ShipRemarksMaster.objects.filter(active=1).order_by("description")
    serializer_class = ShipRemarksMasterListSerializer


#####################################################################################
# Reports related views
@swagger.DARTS_REPORT_API_SCHEMA
class DartsReportAPIView(generics.ListAPIView):
    """API view for DARTs Report in Operational Maintenance."""

    serializer_class = DartsReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = DartsReportFilter

    def get_queryset(self):
        report_def = get_report_definition("darts-report")
        if report_def:
            return report_def.get_queryset()
        return InitiateDart.objects.all().order_by("-pk")


@swagger.CLOSED_DARTS_REPORT_API_SCHEMA
class ClosedDartsReportAPIView(generics.ListAPIView):
    """API view for Closed DARTs Report."""

    serializer_class = ClosedDartsReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ClosedDartsReportFilter

    def get_queryset(self):
        report_def = get_report_definition("closed-darts-report")
        if report_def:
            return report_def.get_queryset()
        from django.db.models import Q

        return InitiateDart.objects.filter(
            Q(is_closed=True) | Q(status__iexact="CLOSED")
        ).order_by("-pk")


@swagger.SERVICE_REQUIRED_REPORT_API_SCHEMA
class ServiceRequiredReportAPIView(generics.ListAPIView):
    """API view for Service Required Report."""

    serializer_class = ServiceRequiredReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceRequiredReportFilter

    def get_queryset(self):
        report_def = get_report_definition("service-required-report")
        if report_def:
            return report_def.get_queryset()
        return InitiateDart.objects.all().order_by("-pk")


@swagger.GUARANTEE_MONITORING_REPORT_API_SCHEMA
class GuaranteeMonitoringReportAPIView(generics.ListAPIView):
    """API view for Guarantee Monitoring Report."""

    serializer_class = GuaranteeMonitoringReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GuaranteeMonitoringReportFilter

    def get_queryset(self):
        report_def = get_report_definition("guarantee-monitoring-report")
        if report_def:
            return report_def.get_queryset()
        return InitiateDart.objects.all().order_by("-pk")


@swagger.SPARES_CONSUMED_REPORT_API_SCHEMA
class SparesConsumedReportAPIView(generics.ListAPIView):
    """API view for Spares Consumed Report."""

    serializer_class = SparesConsumedReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SparesConsumedReportFilter

    def get_queryset(self):
        report_def = get_report_definition("spares-consumed-report")
        if report_def:
            return report_def.get_queryset()
        return InitiateDart.objects.all().order_by("-pk")


@swagger.RA_STATUS_REPORT_API_SCHEMA
class RaStatusReportAPIView(generics.ListAPIView):
    """API view for RA Status Report."""

    serializer_class = RaStatusReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RaStatusReportFilter

    def get_queryset(self):
        report_def = get_report_definition("ra-status")
        if report_def:
            return report_def.get_queryset()
        return InitiateDart.objects.all().order_by("-pk")


@swagger.OPM_REPORT_FILTER_OPTIONS_SCHEMA
class OPMReportFilterOptionsAPIView(views.APIView):
    """Return filter options for DART reports."""

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status_options": ["OPEN", "IN_PROGRESS", "RECTIFIED", "CLOSED"],
                "date_filter_options": [
                    "last_30_days",
                    "last_90_days",
                    "this_year",
                    "last_year",
                ],
                "severity_options": ["CRITICAL", "MAJOR", "MINOR"],
            }
        )


@swagger.OPM_REPORT_EXPORT_SCHEMA
class OPMReportExportAPIView(views.APIView):
    """Export report to CSV format based on report_key."""

    def post(self, request, report_key, *args, **kwargs):
        report_def = get_report_definition(report_key)
        if not report_def:
            return Response(
                {"detail": f"Report '{report_key}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        queryset = apply_filterset(report_def, request.query_params or request.data)
        serializer = report_def.serializer_class(queryset, many=True)
        data = serializer.data

        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)

        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{report_key}.csv"'
        return response


@swagger.OPM_REPORT_EXPORT_JOB_STATUS_SCHEMA
class OPMReportExportJobStatusAPIView(views.APIView):
    """Status check for report export job."""

    def get(self, request, job_id, *args, **kwargs):
        return Response({"job_id": str(job_id), "status": "COMPLETED", "progress": 100})


@swagger.OPM_REPORT_EXPORT_JOB_DOWNLOAD_SCHEMA
class OPMReportExportJobDownloadAPIView(views.APIView):
    """Download export job result file."""

    def get(self, request, job_id, *args, **kwargs):
        return Response({"job_id": str(job_id), "download_url": ""})


@swagger.DEFECTDASHBOARDAPIVIEW_SCHEMA
class DartDashboardViewSet(viewsets.ViewSet):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="period",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="ALL, 6M, 1Y or 2Y",
                enum=["ALL", "6M", "1Y", "2Y"],
            ),
            OpenApiParameter(
                name="department",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                name="activity_period",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=False,
                description="today, week, month, quarter or year",
                enum=[
                    "today",
                    "week",
                    "month",
                    "quarter",
                    "year",
                ],
            ),
        ],
        responses={200: DartDashboardSerializer},
    )
    def list(self, request):
        period = request.query_params.get(
            "period",
            "ALL",
        )

        department = request.query_params.get(
            "department",
        )

        activity_period = request.query_params.get(
            "activity_period",
            "month",
        )

        valid_periods = {
            "ALL",
            "6M",
            "1Y",
            "2Y",
        }

        if period.upper() not in valid_periods:
            return Response(
                {
                    "status": False,
                    "message": ("Invalid period. Use ALL, 6M, 1Y or 2Y."),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_activity_periods = {
            "today",
            "week",
            "month",
            "quarter",
            "year",
        }

        if activity_period.lower() not in valid_activity_periods:
            return Response(
                {
                    "status": False,
                    "message": (
                        "Invalid activity_period. "
                        "Use today, week, month, quarter or year."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = DartDashboardService.get_dashboard(
            period=period.upper(),
            department=department,
            activity_period=activity_period.lower(),
        )

        serializer = DartDashboardSerializer(data)

        return Response(
            {
                "status": True,
                "message": "DART dashboard data fetched successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
