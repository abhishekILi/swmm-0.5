from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "inouttag"

router = DefaultRouter()
router.register("tagouts", views.TagOutViewSet, basename="tagout")
router.register("tagins", views.TagInViewSet, basename="tagin")

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("history/", views.HistoryAPIView.as_view(), name="history"),
    path("", include(router.urls)),
]
