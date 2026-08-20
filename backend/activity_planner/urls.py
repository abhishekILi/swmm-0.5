from rest_framework.routers import DefaultRouter

from .views import EventViewSet, PlannerActivityViewSet

router = DefaultRouter()
router.register(
    r"planner-activities",
    PlannerActivityViewSet,
    basename="planner-activities",
)
router.register(r"", EventViewSet, basename="events")


urlpatterns = router.urls
