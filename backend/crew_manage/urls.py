from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "crew_manage"

router = DefaultRouter()
router.register(
    "leave-applications", views.LeaveApplicationViewSet, basename="leave-application"
)
router.register("civilians", views.CivilianOfficialViewSet, basename="civilian")
router.register("sailings", views.SailingViewSet, basename="sailing")
router.register(
    "action-stations", views.ActionStationMasterViewSet, basename="action-station"
)
router.register(
    "defence-stations", views.DefenceStationMasterViewSet, basename="defence-station"
)
router.register(
    "cruising-stations", views.CruisingStationMasterViewSet, basename="cruising-station"
)
router.register(
    "shelter-stations", views.ShelterStationMasterViewSet, basename="shelter-station"
)
router.register(
    "emergency-stations",
    views.EmergencyStationMasterViewSet,
    basename="emergency-station",
)
router.register(
    "rank-classifications",
    views.SailorRankClassificationViewSet,
    basename="rank-classification",
)

urlpatterns = [
    # personnel status / dashboard data
    path(
        "personnel-status/",
        views.PersonnelStatusView.as_view(),
        name="personnel-status",
    ),
    path(
        "personnel-status/counts/",
        views.PersonnelStatusCountsView.as_view(),
        name="personnel-status-counts",
    ),
    path(
        "personnel-status/update/",
        views.UpdatePersonnelStatusView.as_view(),
        name="personnel-status-update",
    ),
    # leave forecast
    path(
        "leave-forecast/logs/",
        views.LeaveForecastLogsView.as_view(),
        name="leave-forecast-logs",
    ),
    path(
        "leave-forecast/applications/",
        views.LeaveForecastApplicationsView.as_view(),
        name="leave-forecast-applications",
    ),
    # watch station bill
    path(
        "watchbill/dashboard/",
        views.WatchbillDashboardView.as_view(),
        name="watchbill-dashboard",
    ),
    path(
        "watchbill/personnel/",
        views.WatchbillPersonnelListView.as_view(),
        name="watchbill-personnel",
    ),
    # keyed by the SailingPersonnel row's own id — placed before the router
    # include so it's unambiguous relative to the "sailings/<pk>/..." routes.
    path(
        "sailings/personnel/<int:sp_id>/",
        views.SailingPersonnelDetailView.as_view(),
        name="sailing-personnel-detail",
    ),
    path("", include(router.urls)),
]
