from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from master.models import Department, MasterCommand, Ship
from master.utils import get_this_ship

from .models import (
    CustomUser,
    CustomUserProfile,
    Designation,
    GalleryImage,
    LoginRegistrationImage,
    MasterKnowYourRegulator,
    MasterRegulatorDivision,
    Rank,
    Role,
)
from .serializers import (
    AssignSailorsToDivisionSerializer,
    ChangePasswordSerializer,
    CommandSerializer,
    CurrentUserSerializer,
    CustomTokenObtainPairSerializer,
    CustomUserProfileSerializer,
    CustomUserSerializer,
    DeactivateUserSerializer,
    DepartmentSerializer,
    DesignationSerializer,
    GalleryImageSerializer,
    LoginRegistrationImageSerializer,
    MarriageDetailsSerializer,
    MasterKnowYourRegulatorSerializer,
    MasterRegulatorDivisionSerializer,
    PersonnelEventResponseSerializer,
    RankSerializer,
    RegisterProfileSerializer,
    RoleSerializer,
)

RegularManage = "regulator.manage"

# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class LoginView(TokenObtainPairView):
    """POST {username, password} -> {access, refresh, user}."""

    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(tags=["Users"])
class RefreshView(TokenRefreshView):
    permission_classes = (AllowAny,)


@extend_schema(tags=["Users"])
class LogoutView(APIView):
    """POST {refresh} — blacklists the refresh token so it can't be reused."""

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "refresh token required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except (TokenError, AttributeError):
            return Response(
                {"detail": "Invalid or already blacklisted token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Users"])
class MeView(APIView):
    """GET the caller's identity + the capability list the Angular app should
    key its guards/menus off of. See user_drf/permissions.py."""

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)


@extend_schema(tags=["Users"])
class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password changed successfully."})


@extend_schema(tags=["Users"])
class RegisterView(generics.CreateAPIView):
    """Self-service registration — creates a pending account (is_active=False)
    awaiting admin approval, exactly like the legacy Registerview."""

    permission_classes = (AllowAny,)
    serializer_class = RegisterProfileSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(
            {
                "detail": "Account created. Awaiting admin approval.",
                "profile": CustomUserProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
        )


# --------------------------------------------------------------------------
# Read-only master data
# --------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class RankViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RankSerializer
    queryset = Rank.objects.order_by("name")


@extend_schema(tags=["Users"])
class DesignationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DesignationSerializer
    queryset = Designation.objects.all()


@extend_schema(tags=["Users"])
class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoleSerializer
    queryset = Role.objects.all()


@extend_schema(tags=["Users"])
class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.exclude(name__iexact="ADMIN").order_by("name")


@extend_schema(tags=["Users"])
class CommandViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CommandSerializer
    queryset = MasterCommand.objects.all()


# --------------------------------------------------------------------------
# User management
# --------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    """list/retrieve are department-scoped unless the caller has
    'user.view_all'; every mutating action requires 'user.manage'
    (mirrors UserListView / EditUserProfileView / ManageUserView)."""

    serializer_class = CustomUserSerializer
    http_method_names = ("get", "patch", "post", "head", "options")

    def get_queryset(self):
        qs = CustomUser.objects.select_related(
            "user_profile__department",
            "user_profile__role_master",
            "user_profile__designation_master",
        ).filter(user_profile__isnull=False)
        if self.action == "list":
            qs = self.scope_queryset_to_department(qs, self.request)
        return qs

    def scope_queryset_to_department(self, qs, request):
        """Restricts the list to the caller's own department unless they're
        an admin (mirrors the legacy UserListView department scoping)."""
        user = request.user
        if user.is_admin or user.department is None:
            return qs
        return qs.filter(user_profile__department_id=user.department_id)

    def partial_update(self, request, *args, **kwargs):
        """Updates both CustomUser fields (username/is_active) and the nested
        profile in one call, mirroring EditUserProfileView."""
        user = self.get_object()
        profile = user.user_profile

        profile_data = {
            k: v for k, v in request.data.items() if k not in ("username", "is_active")
        }
        if profile_data:
            profile_serializer = CustomUserProfileSerializer(
                profile, data=profile_data, partial=True
            )
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()

        if "username" in request.data:
            user.username = str(request.data["username"]).upper()
        if "is_active" in request.data:
            user.is_active = request.data["is_active"]
        user.save()

        return Response(CustomUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        if user.user_profile is not None:
            user.user_profile.user_active = True
            user.user_profile.is_role = True
            user.user_profile.save()
        return Response(CustomUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def disapprove(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save()
        if user.user_profile is not None:
            user.user_profile.user_active = False
            user.user_profile.save()
        return Response(CustomUserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        serializer = DeactivateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user.user_profile)
        return Response(CustomUserSerializer(user).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="pending-count",
    )
    def pending_count(self, request):
        return Response(
            {"count": CustomUserProfile.objects.filter(is_role=False).count()}
        )


@extend_schema(tags=["Users"])
class MarriageDetailsView(APIView):
    def get(self, request, pk):
        profile = get_object_or_404(
            CustomUserProfile.objects.select_related("rank"), pk=pk
        )
        return Response(MarriageDetailsSerializer(profile).data)

    def patch(self, request, pk):
        profile = get_object_or_404(CustomUserProfile, pk=pk)
        profile.marriage_date = request.data.get("marriage_date")
        profile.is_married = True
        profile.save()
        return Response(MarriageDetailsSerializer(profile).data)


# --------------------------------------------------------------------------
# Regulator hierarchy ("Know Your Regulator")
# --------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class MasterRegulatorDivisionViewSet(viewsets.ModelViewSet):
    serializer_class = MasterRegulatorDivisionSerializer

    def get_queryset(self):
        qs = MasterRegulatorDivision.objects.select_related("department", "regulator")
        department_id = self.request.query_params.get("department")
        regulator_id = self.request.query_params.get("regulator")
        if department_id:
            qs = qs.filter(department_id=department_id)
        if regulator_id:
            qs = qs.filter(regulator_id=regulator_id)
        return qs


@extend_schema(tags=["Users"])
class MasterKnowYourRegulatorViewSet(viewsets.ModelViewSet):
    serializer_class = MasterKnowYourRegulatorSerializer

    def get_queryset(self):
        qs = MasterKnowYourRegulator.objects.select_related(
            "department", "regulator", "division", "sailor"
        )
        department_id = self.request.query_params.get("department")
        if department_id:
            qs = qs.filter(department_id=department_id)
        return qs

    def perform_destroy(self, instance):
        if instance.sailor is not None:
            instance.sailor.division = None
            instance.sailor.save()
        instance.delete()


@extend_schema(tags=["Users"])
class RegulatorLookupView(APIView):
    """GET ?department=<id> -> CustomUserProfile rows with role 'Regulator'
    in that department (replaces get_regulators_by_department)."""

    def get(self, request):
        department_id = request.query_params.get("department")
        qs = CustomUserProfile.objects.filter(role_master__role_name="Regulator")
        if department_id:
            qs = qs.filter(department_id=department_id)
        return Response([{"id": r.id, "name": r.firstname} for r in qs])


@extend_schema(tags=["Users"])
class SailorLookupView(APIView):
    """GET ?department=<id> -> unassigned CustomUserProfile rows with role
    'Sailor' in that department (replaces get_sailors_by_department)."""

    def get(self, request):
        department_id = request.query_params.get("department")
        qs = CustomUserProfile.objects.filter(
            role_master__role_name="Sailor", division__isnull=True
        )
        if department_id:
            qs = qs.filter(department_id=department_id)
        return Response([{"id": s.id, "name": s.firstname} for s in qs])


@extend_schema(tags=["Users"])
class AssignSailorsToDivisionView(APIView):
    required_capability = RegularManage

    def post(self, request):
        serializer = AssignSailorsToDivisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        division = serializer.save()
        return Response(MasterRegulatorDivisionSerializer(division).data)


@extend_schema(tags=["Users"])
class ShipHierarchyView(APIView):
    """Reproduces get_ship_hierarchy: builds the ship -> department ->
    regulator -> division -> sailor tree for the caller's own department."""

    def get(self, request, ship_id):
        ship_obj = self._get_ship(ship_id)

        if not ship_obj:
            return Response(
                {"error": "Ship not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        nodes = [self._build_ship_node(ship_obj)]

        profile = request.user.CustomUser_profile
        departments = self._get_departments(profile)

        for department in departments:
            dept_node = self._build_department_node(department, nodes)
            self._add_department_nodes(department, dept_node, nodes)

        return Response(nodes)

    def _get_ship(self, ship_id):
        return Ship.objects.filter(id=ship_id).first()

    def _get_departments(self, profile):
        if not profile:
            return Department.objects.none()

        return Department.objects.filter(id=profile.department_id)

    def _build_ship_node(self, ship):
        return {
            "id": f"ship_{ship.id}",
            "name": ship.name,
            "designation": "SHIP",
            "rank": "SHIP",
            "personal_number": "",
            "photo_url": getattr(
                ship,
                "photo_url",
                "/static/users/img/ship.png",
            ),
            "parent_id": None,
            "collapsed": True,
            "hasChildren": True,
        }

    def _build_department_node(self, department, nodes):
        node = {
            "id": f"dept_{department.id}",
            "name": department.name,
            "designation": "Department",
            "rank": "DEPT",
            "personal_number": "",
            "photo_url": "/static/users/img/department1.png",
            "parent_id": nodes[0]["id"],
            "collapsed": True,
            "hasChildren": True,
        }

        nodes.append(node)
        return node

    def _add_department_nodes(self, department, dept_node, nodes):
        regulators = MasterRegulatorDivision.objects.filter(
            department=department
        ).select_related(
            "regulator",
            "regulator__designation_master",
            "regulator__rank",
        )

        for reg_div in regulators:
            regulator = reg_div.regulator

            reg_node = self._build_regulator_node(
                regulator,
                dept_node,
                nodes,
            )

            self._add_regulator_divisions(
                regulator,
                department,
                reg_node,
                nodes,
            )

    def _build_regulator_node(self, regulator, dept_node, nodes):
        designation = regulator.designation or (
            regulator.designation_master.designation_name
            if regulator.designation_master
            else ""
        )

        node = {
            "id": f"reg_{regulator.id}",
            "name": f"{regulator.firstname} {regulator.lastname}",
            "designation": designation,
            "rank": regulator.rank.name if regulator.rank_id else "",
            "personal_number": regulator.personal_number or "",
            "photo_url": getattr(
                regulator,
                "photo_url",
                "/static/users/img/Regulator1.png",
            ),
            "parent_id": dept_node["id"],
            "collapsed": True,
            "hasChildren": True,
        }

        nodes.append(node)
        return node

    def _add_regulator_divisions(
        self,
        regulator,
        department,
        reg_node,
        nodes,
    ):
        divisions = MasterRegulatorDivision.objects.filter(
            regulator=regulator,
            department=department,
        )

        for division in divisions:
            div_node = self._build_division_node(
                division,
                reg_node,
                nodes,
            )

            self._add_division_sailors(
                division,
                regulator,
                department,
                div_node,
                nodes,
            )

    def _build_division_node(self, division, reg_node, nodes):
        node = {
            "id": f"div_{division.id}",
            "name": division.division,
            "designation": "Division",
            "rank": "DIV",
            "personal_number": "",
            "photo_url": "/static/users/img/division1.png",
            "parent_id": reg_node["id"],
            "collapsed": True,
            "hasChildren": True,
        }

        nodes.append(node)
        return node

    def _add_division_sailors(
        self,
        division,
        regulator,
        department,
        div_node,
        nodes,
    ):
        sailors = MasterKnowYourRegulator.objects.filter(
            division=division,
            regulator=regulator,
            department=department,
        ).select_related(
            "sailor",
            "sailor__designation_master",
            "sailor__rank",
        )

        for relation in sailors:
            sailor = relation.sailor

            if not sailor:
                continue

            nodes.append(
                self._build_sailor_node(
                    sailor,
                    div_node,
                )
            )

    def _build_sailor_node(self, sailor, div_node):
        designation = sailor.designation or (
            sailor.designation_master.designation_name
            if sailor.designation_master
            else ""
        )

        return {
            "id": f"sailor_{sailor.id}",
            "name": f"{sailor.firstname} {sailor.lastname}",
            "designation": designation,
            "rank": sailor.rank.name if sailor.rank_id else "",
            "personal_number": sailor.personal_number or "",
            "photo_url": getattr(
                sailor,
                "photo_url",
                "/static/images/user.png",
            ),
            "parent_id": div_node["id"],
            "collapsed": False,
            "hasChildren": False,
        }


# --------------------------------------------------------------------------
# Login / registration page images
# --------------------------------------------------------------------------


@extend_schema(tags=["Users"])
class LoginRegistrationImageViewSet(viewsets.ModelViewSet):
    """list is public (shown on the pre-auth login page); writes require
    'login_image.manage'."""

    serializer_class = LoginRegistrationImageSerializer
    queryset = LoginRegistrationImage.objects.filter(is_active=True).order_by(
        "-uploaded_at"
    )

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        return super().get_permissions()


@extend_schema(tags=["Users"])
class GalleryImageViewSet(viewsets.ModelViewSet):
    serializer_class = GalleryImageSerializer
    queryset = GalleryImage.objects.all()

    def get_permissions(self):
        if self.action == "list":
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()

        ship_id = self.request.query_params.get("ship_id")

        if ship_id:
            queryset = queryset.filter(ship_id=ship_id)
        else:
            ship = get_this_ship()
            if not ship:
                return queryset.none()
            queryset = queryset.filter(ship=ship)

        return queryset.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ship = get_this_ship()
        image = serializer.save(ship=ship)

        return Response(
            {
                "status": "success",
                "message": "Image uploaded",
                "data": GalleryImageSerializer(image).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.image:
            instance.image.delete(save=False)

        instance.delete()

        return Response(
            {
                "status": "success",
                "message": "Image deleted",
            }
        )


def ordinal(number):
    """Return a number with its ordinal suffix."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {
            1: "st",
            2: "nd",
            3: "rd",
        }.get(number % 10, "th")

    return f"{number}{suffix}"


def get_next_annual_date(event_date, today):
    """
    Get the next occurrence of an annual event.

    February 29 is treated as March 1 in non-leap years.
    """
    month_day = (event_date.month, event_date.day)

    try:
        current_occurrence = date(today.year, *month_day)
    except ValueError:
        current_occurrence = date(today.year, 3, 1)

    if current_occurrence >= today:
        return current_occurrence

    try:
        return date(today.year + 1, *month_day)
    except ValueError:
        return date(today.year + 1, 3, 1)


def get_user_name(user):
    """Return the user's full name."""
    return f"{user.firstname or ''} {user.lastname or ''}".strip()


def get_user_designation(user):
    """Return the user's configured designation."""
    if user.designation:
        return user.designation

    if user.designation_master:
        return user.designation_master.designation_name

    return ""


def build_event_base(user, event_type, event_date):
    """Build fields shared by birthday and anniversary events."""
    return {
        "type": event_type,
        "name": get_user_name(user),
        "personal_number": user.personal_number,
        "designation": get_user_designation(user),
        "event_date": event_date,
        "age": None,
        "years": None,
    }


def build_birthday_event(user, today):
    """Create the upcoming birthday event for a user."""
    dob = user.date_of_birth

    if not dob:
        return None

    event_date = get_next_annual_date(dob, today)

    age = event_date.year - dob.year

    event = build_event_base(
        user=user,
        event_type="birthday",
        event_date=event_date,
    )

    event.update(
        {
            "age": age,
            "event_label": f"{ordinal(age)} Birthday",
        }
    )

    return event


def build_anniversary_event(user, today):
    """Create the upcoming marriage anniversary event for a user."""
    marriage_date = user.marriage_date

    if not marriage_date:
        return None

    event_date = get_next_annual_date(marriage_date, today)

    years = event_date.year - marriage_date.year

    event = build_event_base(
        user=user,
        event_type="anniversary",
        event_date=event_date,
    )

    event.update(
        {
            "years": years,
            "event_label": f"{ordinal(years)} Anniversary",
        }
    )

    return event


def is_within_range(event_date, start_date, end_date):
    """Check whether an event falls inside the requested date range."""
    return start_date <= event_date <= end_date


def get_user_events(user, today, end_date):
    """Return all qualifying events for a user."""
    events = []

    birthday = build_birthday_event(user, today)

    if birthday and is_within_range(
        birthday["event_date"],
        today,
        end_date,
    ):
        events.append(birthday)

    anniversary = build_anniversary_event(user, today)

    if anniversary and is_within_range(
        anniversary["event_date"],
        today,
        end_date,
    ):
        events.append(anniversary)

    return events


def group_events_by_date(events, today):
    """Group events into today, tomorrow and upcoming."""
    tomorrow = today + timedelta(days=1)

    grouped = {
        "today": [],
        "tomorrow": [],
        "upcoming": [],
    }

    for event in events:
        event_date = event["event_date"]

        if event_date == today:
            grouped["today"].append(event)
        elif event_date == tomorrow:
            grouped["tomorrow"].append(event)
        else:
            grouped["upcoming"].append(event)

    return grouped


def get_upcoming_events():
    """
    Build upcoming birthday and anniversary events.

    Returns events occurring today or during the next 7 days.
    """
    today = timezone.now().date()
    end_date = today + timedelta(days=7)

    users = CustomUserProfile.objects.select_related("rank", "designation_master").all()

    events = []

    for user in users:
        events.extend(
            get_user_events(
                user=user,
                today=today,
                end_date=end_date,
            )
        )

    events.sort(key=lambda event: event["event_date"])

    grouped = group_events_by_date(
        events=events,
        today=today,
    )

    return today, end_date, events, grouped


@extend_schema(tags=["Users"])
class PersonnelEventsAPIView(APIView):
    """
    Return birthdays and marriage anniversaries occurring
    today or within the next 7 days.
    """

    permission_classes = (AllowAny,)

    def get(self, request):
        today, end_date, events, grouped = get_upcoming_events()

        data = {
            "status": "success",
            "count": len(events),
            "from_date": today,
            "to_date": end_date,
            "today": grouped["today"],
            "tomorrow": grouped["tomorrow"],
            "upcoming": grouped["upcoming"],
            "results": events,
        }

        serializer = PersonnelEventResponseSerializer(data)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
