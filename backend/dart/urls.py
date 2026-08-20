from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssistanceMasterListAPIView,
    CertificateTypeMasterListAPIView,
    ClosedDartsReportAPIView,
    DartDashboardViewSet,
    DartsReportAPIView,
    GuaranteeMonitoringReportAPIView,
    OPMReportExportAPIView,
    OPMReportExportJobDownloadAPIView,
    OPMReportExportJobStatusAPIView,
    OPMReportFilterOptionsAPIView,
    RaStatusReportAPIView,
    ReasonMasterListAPIView,
    RepairAgencyMasterListAPIView,
    ServiceRequiredReportAPIView,
    ServicesMasterListAPIView,
    SeverityMasterListAPIView,
    ShipRemarksMasterListAPIView,
    SparesConsumedReportAPIView,
)

router = DefaultRouter()

router.register(
    r"dashboard",
    DartDashboardViewSet,
    basename="dart-dashboard",
)

urlpatterns = [
    path(
        "configuration/repair-agency-master/",
        RepairAgencyMasterListAPIView.as_view(),
        name="op-maintenance-repair-agency-master",
    ),
    # Vatsal
    path(
        "configuration/assistance-master/",
        AssistanceMasterListAPIView.as_view(),
        name="op-maintenance-assistance-master",
    ),
    path(
        "configuration/reason-master/",
        ReasonMasterListAPIView.as_view(),
        name="op-maintenance-reason-master",
    ),
    path(
        "configuration/severity-master/",
        SeverityMasterListAPIView.as_view(),
        name="op-maintenance-severity-master",
    ),
    path(
        "configuration/services-master/",
        ServicesMasterListAPIView.as_view(),
        name="op-maintenance-services-master",
    ),
    path(
        "configuration/certificate-type-master/",
        CertificateTypeMasterListAPIView.as_view(),
        name="op-maintenance-certificate-type-master",
    ),
    path(
        "configuration/ship-remarks-master/",
        ShipRemarksMasterListAPIView.as_view(),
        name="op-maintenance-ship-remarks-master",
    ),
    #############################################################################
    # Reports
    #############################################################################
    path("reports/darts/", DartsReportAPIView.as_view(), name="opm-darts-report"),
    path(
        "reports/closed-darts/",
        ClosedDartsReportAPIView.as_view(),
        name="opm-closed-darts-report",
    ),
    path(
        "reports/service-required/",
        ServiceRequiredReportAPIView.as_view(),
        name="opm-service-required-report",
    ),
    path(
        "reports/guarantee-monitoring/",
        GuaranteeMonitoringReportAPIView.as_view(),
        name="opm-guarantee-monitoring-report",
    ),
    path(
        "reports/spares-consumed/",
        SparesConsumedReportAPIView.as_view(),
        name="opm-spares-consumed-report",
    ),
    path(
        "reports/ra-status/",
        RaStatusReportAPIView.as_view(),
        name="opm-ra-status-report",
    ),
    path(
        "reports/filter-options/",
        OPMReportFilterOptionsAPIView.as_view(),
        name="opm-report-filter-options",
    ),
    path(
        "reports/export-jobs/<uuid:job_id>/download/",
        OPMReportExportJobDownloadAPIView.as_view(),
        name="opm-report-export-job-download",
    ),
    path(
        "reports/export-jobs/<uuid:job_id>/",
        OPMReportExportJobStatusAPIView.as_view(),
        name="opm-report-export-job-status",
    ),
    path(
        "reports/<str:report_key>/export/",
        OPMReportExportAPIView.as_view(),
        name="opm-report-export",
    ),
    path("", include(router.urls)),
]
