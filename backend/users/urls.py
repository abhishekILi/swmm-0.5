from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "users"

router = DefaultRouter()
router.register("ranks", views.RankViewSet, basename="rank")
router.register("designations", views.DesignationViewSet, basename="designation")
router.register("roles", views.RoleViewSet, basename="role")
router.register("departments", views.DepartmentViewSet, basename="department")
router.register("commands", views.CommandViewSet, basename="command")
router.register("users", views.UserViewSet, basename="user")
router.register(r"gallery", views.GalleryImageViewSet, basename="gallery")
router.register(
    "regulator-divisions",
    views.MasterRegulatorDivisionViewSet,
    basename="regulator-division",
)
router.register(
    "know-your-regulator",
    views.MasterKnowYourRegulatorViewSet,
    basename="know-your-regulator",
)
router.register(
    "login-images", views.LoginRegistrationImageViewSet, basename="login-image"
)

urlpatterns = [
    # auth
    path("token/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("me/", views.MeView.as_view(), name="me"),
    path(
        "me/change-password/",
        views.ChangePasswordView.as_view(),
        name="change-password",
    ),
    # regulator hierarchy lookups
    path("regulators/", views.RegulatorLookupView.as_view(), name="regulator-lookup"),
    path("sailors/", views.SailorLookupView.as_view(), name="sailor-lookup"),
    path(
        "regulator-divisions/assign-sailors/",
        views.AssignSailorsToDivisionView.as_view(),
        name="assign-sailors",
    ),
    path(
        "ships/<int:ship_id>/hierarchy/",
        views.ShipHierarchyView.as_view(),
        name="ship-hierarchy",
    ),
    # profile utilities
    path(
        "profiles/<int:pk>/marriage/",
        views.MarriageDetailsView.as_view(),
        name="marriage-details",
    ),
    path(
        "personnel-events/",
        views.PersonnelEventsAPIView.as_view(),
        name="personnel-events",
    ),
    path("", include(router.urls)),
]
