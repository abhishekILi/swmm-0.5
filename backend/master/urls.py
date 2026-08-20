from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CoMessageViewSet,
    ExportRoutineExcelAPIView,
    HierarchyForChartViewSet,
    ImportExcelFileView,
    KnowYourShipAPIView,
    MaintenanceNomenclatureAPIView,
    MaintenanceNomenclatureDeleteAPIView,
    MemberDetailViewSet,
    OrderDutyViewSet,
    QuoteViewSet,
    RefitCompletionsView,
    RefitDelinquencyView,
    RefitDryDockView,
    RefitOcrView,
    # Integration Views
    RefitPayloadView,
    ShipRoleViewSet,
    UpdateEntryViewSet,
)

router = DefaultRouter()
router.register(r"update-entries", UpdateEntryViewSet, basename="updateentry")
router.register(r"ship-roles", ShipRoleViewSet, basename="shiprole")
router.register(r"member-details", MemberDetailViewSet, basename="memberdetail")
router.register(r"order-duties", OrderDutyViewSet, basename="orderduty")
router.register(r"quotes", QuoteViewSet, basename="quote")
router.register(r"co-messages", CoMessageViewSet, basename="comessage")
router.register(r"hierarchy", HierarchyForChartViewSet, basename="hierarchy")

urlpatterns = [
    # path("import-excel/", ImportExcelFileView.as_view(), name="import_excel"),
    path("", include(router.urls)),
    # Expose ImportExcelFile endpoint at /api/v1/master/import-excel/
    path("master/import-excel/", ImportExcelFileView.as_view(), name="import_excel"),
    path(
        "ships/know-your-ship/",
        KnowYourShipAPIView.as_view(),
        name="know-your-ship",
    ),
    path(
        "export-routine-excel/",
        ExportRoutineExcelAPIView.as_view(),
        name="export-routine-excel",
    ),
    path(
        "maintenance-nomenclature/",
        MaintenanceNomenclatureAPIView.as_view(),
        name="maintenance-nomenclature",
    ),
    path(
        "maintenance-nomenclature/delete/",
        MaintenanceNomenclatureDeleteAPIView.as_view(),
        name="maintenance-nomenclature-delete",
    ),
]


integration_urlpatterns = [
    # CMMS Refit Paths
    path(
        "cmms/refit",
        RefitPayloadView.as_view(),
        name="cmms-refit-payload",
    ),
    path(
        "cmms/refit/completions",
        RefitCompletionsView.as_view(),
        name="cmms-refit-completions",
    ),
    path(
        "cmms/refit/completions/<str:uid>/delinquency",
        RefitDelinquencyView.as_view(),
        name="cmms-refit-delinquency",
    ),
    path(
        "cmms/refit/completions/<str:uid>/drydock",
        RefitDryDockView.as_view(),
        name="cmms-refit-drydock",
    ),
    path(
        "cmms/refit/completions/<str:uid>/ocr",
        RefitOcrView.as_view(),
        name="cmms-refit-ocr",
    ),
]
