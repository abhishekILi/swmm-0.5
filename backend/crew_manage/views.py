"""
Views for crewmanage_drf — class-based only (APIView / ModelViewSet), with
permission_classes set explicitly per view/action, mirroring user_drf/views.py.

See the module docstrings in serializers.py and permissions.py for the
shared helpers and RBAC plumbing imported below.
"""

from datetime import datetime, timedelta

from django.db.models import CharField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from master.models import Department
from users.models import CustomUserProfile

from .models import (
    ActionStationMaster,
    CivilianOfficial,
    CruisingStationMaster,
    DefenceStationMaster,
    EmergencyStationMaster,
    LeaveApplication,
    PersonnelAssignment,
    PersonnelStatusLog,
    Sailing,
    SailingPersonnel,
    SailorRankClassification,
    ShelterStationMaster,
)
from .serializers import (
    ActionStationMasterSerializer,
    ApplyOnBehalfSerializer,
    AssignmentsSaveSerializer,
    CivilianOfficialSerializer,
    CruisingStationMasterSerializer,
    DefenceStationMasterSerializer,
    EmergencyStationMasterSerializer,
    LeaveApplicationSerializer,
    LeaveDatesUpdateSerializer,
    PersonnelStatusRowSerializer,
    SailingCompleteSerializer,
    SailingCreateSerializer,
    SailingListSerializer,
    SailorRankClassificationSerializer,
    ShelterStationMasterSerializer,
    TruncateLeaveSerializer,
    UpdatePersonnelStatusSerializer,
    _absent_pnos,
    _delete_status_logs,
    _get_profile,
    _log_status_range,
    _role_name,
)

OnLeave = "On Leave"
TyDuty = "Ty Duty"

# ==========================================================================
# Personnel status / dashboard data
# ==========================================================================


@extend_schema(tags=["Ship Crew"])
class PersonnelStatusView(APIView):
    """GET personnel-status/?status=present|leave|ty|all -> get_status_data
    (crewmanage/views.py:26)."""

    def get(self, request):
        status_param = request.query_params.get("status")
        today = timezone.now().date()

        latest_status_subquery = (
            PersonnelStatusLog.objects.filter(
                personnel_number=OuterRef("personal_number"), log_date=today
            )
            .order_by("-created_at")
            .values("status")[:1]
        )

        queryset = (
            CustomUserProfile.objects.annotate(
                latest_status=Coalesce(
                    Subquery(latest_status_subquery),
                    Value("Present"),
                    output_field=CharField(),
                )
            )
            .select_related("rank", "designation_master", "department")
            .filter(user_active=True)
        )

        if status_param:
            status_param = status_param.lower()
            if status_param == "present":
                queryset = queryset.filter(latest_status="Present")
            elif status_param == "leave":
                queryset = queryset.filter(latest_status=OnLeave)
            elif status_param == "ty":
                queryset = queryset.filter(latest_status=TyDuty)
            # "all" (or anything else) -> no extra filtering, matches legacy.

        personnel = queryset.values(
            "id",
            "rank__name",
            "firstname",
            "lastname",
            "personal_number",
            "department__name",
            "designation_master__designation_name",
            "latest_status",
        ).order_by("rank__name", "firstname")

        serializer = PersonnelStatusRowSerializer(personnel, many=True)
        return Response({"data": serializer.data})


@extend_schema(tags=["Ship Crew"])
class PersonnelStatusCountsView(APIView):
    """GET personnel-status/counts/ -> get_counts (crewmanage/views.py:124)."""

    def get(self, request):
        today = timezone.localdate()

        latest_status_subquery = (
            PersonnelStatusLog.objects.filter(
                personnel_number=OuterRef("personal_number"), log_date=today
            )
            .order_by("-created_at")
            .values("status")[:1]
        )

        queryset = CustomUserProfile.objects.annotate(
            latest_status=Coalesce(
                Subquery(latest_status_subquery),
                Value("Present"),
                output_field=CharField(),
            )
        ).filter(user_active=True)

        total = queryset.count()
        present = queryset.filter(latest_status="Present").count()
        on_leave = queryset.filter(latest_status=OnLeave).count()
        ty_duty = queryset.filter(latest_status=TyDuty).count()

        return Response(
            {
                "date": today.strftime("%d-%b-%Y"),
                "total": total,
                "present": present,
                "on_leave": on_leave,
                "ty_duty": ty_duty,
            }
        )


@extend_schema(tags=["Ship Crew"])
class UpdatePersonnelStatusView(APIView):
    """POST personnel-status/update/ -> update_personnel_status
    (crewmanage/views.py:157). Legacy required the caller's role to be
    exactly 'Head of Department' — that's exactly what the
    'crew.status.manage' capability encodes (see user_drf/permissions.py)."""

    def post(self, request):
        serializer = UpdatePersonnelStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_taken = serializer.save()
        return Response({"success": True, "action": action_taken})


# ==========================================================================
# Leave applications
# ==========================================================================


@extend_schema(tags=["Ship Crew"])
class LeaveApplicationViewSet(viewsets.ModelViewSet):
    """
    Endpoint map (legacy originals in crewmanage/views.py):
      list                         -> my_leave_applications (:443) / my_leaves (:1605),
                                       collapsed into one "own applications" list.
                                       ?mine=true is accepted as a no-op alias —
                                       list() is already scoped to the caller.
      create                       -> apply_leave_request (:1462)
      retrieve                    -> NEW (no legacy equivalent) — owner or an
                                       approver ('crew.leave.approve') only.
      apply_on_behalf (POST)       -> hod_apply_leave_for_personnel (:1524,
                                       the ACTIVE definition; the dead commented
                                       copy at :230-331 is ignored)
      pending (GET)                -> pending_leaves (:1624)
      take_action (POST, url 'action') -> action_leave (:1656)
      truncate (POST)              -> truncate_leave (:393) — TIGHTENED: legacy
                                       had ZERO auth/permission check at all (any
                                       caller could truncate any leave by id).
                                       Now requires 'crew.leave.approve'.
      partial_update (PATCH)       -> update_leave_dates (:1265) — TIGHTENED:
                                       same as above, now requires
                                       'crew.leave.approve'.
      destroy (DELETE)             -> delete_leave (:1321) — TIGHTENED: same as
                                       above. Legacy also never `return`ed for
                                       non-DELETE verbs there (a framework bug);
                                       DRF's destroy() is only ever wired to the
                                       DELETE verb by the router, so that can't
                                       recur here.
      check_conflict (GET)         -> check_leave_conflict (:335)

    apply_leave (crewmanage/views.py:211) is intentionally NOT ported — a
    confirmed dead/buggy duplicate of apply_leave_request, excluded per an
    explicit decision recorded in this app's implementation brief.
    """

    serializer_class = LeaveApplicationSerializer
    http_method_names = ("get", "post", "patch", "delete", "head", "options")

    def get_queryset(self):
        qs = LeaveApplication.objects.select_related(
            "applied_by", "approved_rejected_by"
        )
        if self.action == "list":
            profile = _get_profile(self.request.user)
            return qs.filter(applied_by=profile) if profile else qs.none()
        return qs

    # ------------------------------------------------------------------
    # PATCH {id}/ — update_leave_dates (tightened, see class docstring)
    # ------------------------------------------------------------------
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = LeaveDatesUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(instance)
        return Response(self.get_serializer(instance).data)

    # ------------------------------------------------------------------
    # DELETE {id}/ — delete_leave (tightened, see class docstring)
    # ------------------------------------------------------------------
    def perform_destroy(self, instance):
        _delete_status_logs(instance)
        instance.delete()

    # ------------------------------------------------------------------
    # GET check_conflict/ — check_leave_conflict
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="check_conflict")
    def check_conflict(self, request):
        personal_number = request.query_params.get("personal_number", "").strip()
        if not personal_number:
            return Response({"has_conflict": False})

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        conflict = (
            LeaveApplication.objects.filter(
                personal_number=personal_number,
                application_status="Approved",
                start_date__lte=today,
                end_date__gte=today,
            )
            .order_by("-applied_at")
            .first()
        )
        if not conflict:
            return Response({"has_conflict": False})

        current_log = (
            PersonnelStatusLog.objects.filter(
                personnel_number=personal_number, log_date=today
            )
            .order_by("-created_at")
            .first()
        )
        current_status = current_log.status if current_log else conflict.leave_type

        def fmt(d):
            # NOTE: legacy used '%-d' (no leading zero) which raises
            # ValueError on Windows (it's a glibc-only strftime extension).
            # '%d' below is portable and carries the same information.
            return d.strftime("%d %b %Y") if d else ""

        return Response(
            {
                "has_conflict": True,
                "application_id": conflict.id,
                "leave_type": conflict.leave_type,
                "start_date": fmt(conflict.start_date),
                "end_date": fmt(conflict.end_date),
                "new_end_date": yesterday.strftime("%Y-%m-%d"),
                "current_status": current_status,
            }
        )

    # ------------------------------------------------------------------
    # POST {id}/truncate/ — truncate_leave (TIGHTENED, see class docstring)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"])
    def truncate(self, request, pk=None):
        instance = self.get_object()
        serializer = TruncateLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(instance)
        return Response({"success": True, "new_end_date": str(instance.end_date)})

    # ------------------------------------------------------------------
    # POST apply_on_behalf/ — hod_apply_leave_for_personnel
    # ------------------------------------------------------------------
    @action(detail=False, methods=["post"], url_path="apply_on_behalf")
    def apply_on_behalf(self, request):
        serializer = ApplyOnBehalfSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        leave_app = serializer.save()
        return Response(
            {
                "status": "success",
                "message": f"Leave applied for {leave_app.no_of_days} day(s)",
                "no_of_days": leave_app.no_of_days,
                "application_id": leave_app.id,
            },
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # GET pending/ — pending_leaves
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        profile = _get_profile(request.user)
        role = _role_name(profile)
        status_filter = request.query_params.get("status", "Pending")

        qs = LeaveApplication.objects.order_by("-applied_at")
        # CO/COMMAND sees everything; HOD/DY-HOD scoped to their own department.
        if role not in ("co", "command"):
            dept = profile.department.name if profile and profile.department else ""
            qs = qs.filter(department=dept)
        if status_filter and status_filter.lower() != "all":
            qs = qs.filter(application_status=status_filter)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # POST {id}/action/ — action_leave
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="action")
    def take_action(self, request, pk=None):
        leave = self.get_object()
        if leave.application_status != "Pending":
            return Response(
                {
                    "status": "error",
                    "message": f"Application already {leave.application_status}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        action_value = str(request.data.get("action", "")).strip()
        rejection_reason = str(request.data.get("rejection_reason", "")).strip()
        if action_value not in ("Approved", "Rejected"):
            return Response(
                {"status": "error", "message": "action must be Approved or Rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = _get_profile(request.user)
        leave.application_status = action_value
        leave.approved_rejected_by = profile
        leave.approved_rejected_at = timezone.now()
        if action_value == "Rejected":
            leave.rejection_reason = rejection_reason
        leave.save()

        if action_value == "Approved":
            _log_status_range(leave)
        else:
            _delete_status_logs(leave)

        return Response(
            {
                "status": "success",
                "action": action_value,
                "message": f"Application {action_value.lower()} successfully.",
            }
        )


# ==========================================================================
# Leave forecast
# ==========================================================================


def _parse_iso_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@extend_schema(tags=["Ship Crew"])
class LeaveForecastLogsView(APIView):
    """GET leave-forecast/logs/?start=&end= -> forecast_logs
    (crewmanage/views.py:631)."""

    def get(self, request):
        start = _parse_iso_date(request.query_params.get("start", ""))
        end = _parse_iso_date(request.query_params.get("end", ""))
        if not start or not end:
            return Response({"data": []})

        logs = (
            PersonnelStatusLog.objects.filter(log_date__gte=start, log_date__lte=end)
            .values(
                "id",
                "personnel_number",
                "rank",
                "name",
                "department",
                "designation",
                "status",
                "log_date",
            )
            .order_by("log_date", "name")
        )

        data = [{**row, "log_date": str(row["log_date"])} for row in logs]
        return Response({"data": data})


@extend_schema(tags=["Ship Crew"])
class LeaveForecastApplicationsView(APIView):
    """GET leave-forecast/applications/?start=&end= -> forecast_applications
    (crewmanage/views.py:681)."""

    def get(self, request):
        start = _parse_iso_date(request.query_params.get("start", ""))
        end = _parse_iso_date(request.query_params.get("end", ""))
        if not start or not end:
            return Response({"data": []})

        apps = (
            LeaveApplication.objects.filter(start_date__lte=end, end_date__gte=start)
            .values(
                "id",
                "personal_number",
                "rank",
                "name",
                "department",
                "designation",
                "leave_type",
                "start_date",
                "end_date",
                "no_of_days",
                "application_status",
                "remark",
                "reason",
                "applied_at",
                "has_prefix",
                "prefix_start_date",
                "suffix_completion_date",
                "station",
            )
            .order_by("-applied_at")
        )

        data = []
        for a in apps:
            data.append(
                {
                    "id": a["id"],
                    "personal_number": a["personal_number"],
                    "rank": a["rank"],
                    "name": a["name"],
                    "department": a["department"],
                    "designation": a["designation"],
                    "leave_type": a["leave_type"],
                    "start_date": str(a["start_date"]),
                    "end_date": str(a["end_date"]),
                    "no_of_days": a["no_of_days"],
                    "station": a["station"],
                    "application_status": a["application_status"],
                    "remark": a["remark"],
                    "reason": a["reason"] or "",
                    "applied_at": (
                        a["applied_at"].strftime("%d %b %Y") if a["applied_at"] else ""
                    ),
                    "has_prefix": a["has_prefix"],
                    "prefix_start_date": (
                        str(a["prefix_start_date"]) if a["prefix_start_date"] else ""
                    ),
                    "suffix_completion_date": (
                        str(a["suffix_completion_date"])
                        if a["suffix_completion_date"]
                        else ""
                    ),
                }
            )
        return Response({"data": data})


# ==========================================================================
# Watch Station Bill
# ==========================================================================


@extend_schema(tags=["Ship Crew"])
class WatchbillDashboardView(APIView):
    """GET watchbill/dashboard/ -> watch_station_bill_dashboard_stats
    (crewmanage/views.py:833)."""

    def get(self, request):
        today = timezone.now().date()
        total = CustomUserProfile.objects.filter(
            user_active=True, ship_leaving_date__isnull=True
        ).count()
        absent_pnos = _absent_pnos(today, today)
        absent = len(absent_pnos)
        present = total - absent

        dept_data = []
        for dept in Department.objects.all().order_by("name"):
            total_count = CustomUserProfile.objects.filter(
                user_active=True, ship_leaving_date__isnull=True, department=dept
            ).count()
            if not total_count:
                continue

            absent_count = (
                PersonnelStatusLog.objects.filter(department=dept.name, log_date=today)
                .values("personnel_number")
                .distinct()
                .count()
            )
            present_count = max(total_count - absent_count, 0)

            dept_data.append(
                {
                    "dept": dept.name,
                    "total": total_count,
                    "present": present_count,
                    "absent": absent_count,
                }
            )

        active_sailings = list(
            Sailing.objects.filter(status="active")
            .order_by("-created_at")
            .values(
                "id", "name", "area", "start_date", "end_date", "co_name", "created_at"
            )
        )

        return Response(
            {
                "total": total,
                "present": present,
                "absent": absent,
                "active_sailings_count": Sailing.objects.filter(
                    status="active"
                ).count(),
                "completed_sailings_count": Sailing.objects.filter(
                    status="completed"
                ).count(),
                "dept_strength": dept_data,
                "active_sailings": active_sailings,
            }
        )


@extend_schema(tags=["Ship Crew"])
class WatchbillPersonnelListView(APIView):
    """GET watchbill/personnel/ -> watch_station_bill_personnel_list
    (crewmanage/views.py:887)."""

    def _get_personnel_status(self, personal_number, today, absent_pnos):
        if personal_number not in absent_pnos:
            return "Present"

        leave = LeaveApplication.objects.filter(
            personal_number=personal_number,
            application_status="Approved",
            start_date__lte=today,
            end_date__gte=today,
        ).first()

        return leave.leave_type if leave else "Absent"

    def _get_designation(self, profile):
        if profile.designation:
            return profile.designation

        if profile.designation_master:
            return profile.designation_master.designation_name

        return ""

    def _serialize_personnel(self, profile, today, absent_pnos):
        return {
            "id": profile.id,
            "rank": profile.rank.name if profile.rank else "",
            "fname": profile.firstname,
            "lname": profile.lastname,
            "pno": profile.personal_number,
            "dept": profile.department.name if profile.department else "",
            "desig": self._get_designation(profile),
            "doj": (
                str(profile.ship_joining_date.date())
                if profile.ship_joining_date
                else ""
            ),
            "status": self._get_personnel_status(
                profile.personal_number,
                today,
                absent_pnos,
            ),
        }

    def get(self, request):
        today = timezone.now().date()
        absent_pnos = _absent_pnos(today, today)

        qs = (
            CustomUserProfile.objects.filter(
                user_active=True,
                ship_leaving_date__isnull=True,
            )
            .select_related("rank", "department", "designation_master")
            .order_by("department__name", "rank__name")
        )

        data = [
            self._serialize_personnel(profile, today, absent_pnos) for profile in qs
        ]

        return Response({"personnel": data})


@extend_schema(tags=["Ship Crew"])
class CivilianOfficialViewSet(viewsets.ModelViewSet):
    """
    list/create/{id}/deactivate/ — replaces watch_station_bill_civilian_list
    (:1838, the ACTIVE definition), _civilian_add (:1851), _civilian_remove
    (:1878, a soft-delete via is_active=False) with one router ViewSet.

    All watch-station-bill endpoints require only IsAccountActive — legacy
    behavior here was plain @login_required, no extra role gate, so no
    capability requirement is added (that would be scope-creep beyond what
    was decided).
    """

    serializer_class = CivilianOfficialSerializer
    http_method_names = (
        "get",
        "post",
        "head",
        "options",
        "delete",
    )

    def get_queryset(self):
        # Matches watch_station_bill_civilian_list exactly, including its
        # lack of an is_active filter (deactivated civilians remain listed
        # here — a pre-existing legacy quirk, preserved as ground truth).
        return CivilianOfficial.objects.filter(
            ~Q(person_type=""), person_type__isnull=False
        ).order_by("role", "name_snapshot")

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        civilian = get_object_or_404(CivilianOfficial, pk=pk)
        civilian.is_active = False
        civilian.save()
        return Response({"status": "ok"})


@extend_schema(tags=["Ship Crew"])
class SailingViewSet(viewsets.ModelViewSet):
    """
    list/create/retrieve/{id}/complete/destroy — replaces
    watch_station_bill_sailings_list (:1892), _sailing_create (:2495, the
    FINAL/ACTIVE definition — two earlier dead/commented copies are
    ignored), _sailing_detail (:1950), _sailing_complete (:2014),
    _sailing_delete (:2040).
    """

    http_method_names = ("get", "post", "delete", "head", "options")

    def get_queryset(self):
        return Sailing.objects.all()

    def list(self, request, *args, **kwargs):
        status_param = request.query_params.get("status", "active")
        qs = Sailing.objects.filter(status=status_param).order_by("-created_at")
        serializer = SailingListSerializer(qs, many=True)
        return Response({"sailings": serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = SailingCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        sailing = serializer.save()
        return Response(
            {
                "status": "ok",
                "id": sailing.id,
                "copied_personnel": getattr(sailing, "copied_personnel", 0),
                "copied_assignments": getattr(sailing, "copied_assignments", 0),
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_department(self, person):
        return person.dept_snapshot or (
            person.person_type.replace("_", " ").title()
            if person.person_type
            else "Civilian"
        )

    def _get_personnel_data(self, personnel, assign_lookup):
        departments = {}
        civilian_count = 0

        for person in personnel:
            civilian_count += int(
                (person.person_type or "").strip().lower() == "civilian"
            )

            department = self._get_department(person)
            assignment = assign_lookup.get(person.pno_snapshot)

            departments.setdefault(department, []).append(
                self._build_personnel_record(person, assignment)
            )

        return departments, civilian_count

    def _build_personnel_record(self, person, assignment):
        return {
            "rank": person.rank_snapshot,
            "name": person.name_snapshot,
            "pno": person.pno_snapshot,
            "desig": person.desig_snapshot,
            "w3": assignment.w3 if assignment else person.watch_station,
            "w2": assignment.w2 if assignment else "",
            "action": assignment.action if assignment else person.action_station,
            "blood_group": assignment.blood_group if assignment else "",
            "status": person.status_override,
            "mess": assignment.mess if assignment else "",
        }

    def _get_civilian_data(self, civilians):
        return [
            {
                "id": civilian.id,
                "name": civilian.name_snapshot,
                "rank": civilian.rank_snapshot,
                "pno": civilian.pno_snapshot,
                "desig": civilian.desig_snapshot,
                "role": civilian.role,
                "person_type": civilian.person_type,
                "service_no": civilian.service_no,
                "fleet": civilian.fleet,
                "ship": civilian.ship,
                "cid": civilian.cid,
                "contact": civilian.contact,
                "remarks": civilian.remarks,
                "status": civilian.status_override,
            }
            for civilian in civilians
        ]

    def _format_sailing_date(self, value):
        return value.strftime("%d/%m/%Y") if value else ""

    def retrieve(self, request, *args, **kwargs):
        sailing = self.get_object()

        personnel = SailingPersonnel.objects.filter(sailing=sailing)

        civilians = SailingPersonnel.objects.filter(
            ~Q(person_type=""),
            person_type__isnull=False,
            sailing=sailing,
        )

        assign_lookup = {
            assignment.pno: assignment
            for assignment in PersonnelAssignment.objects.filter(sailing=sailing)
        }

        departments, civilian_count = self._get_personnel_data(
            personnel,
            assign_lookup,
        )

        civilian_data = self._get_civilian_data(civilians)

        return Response(
            {
                "id": sailing.id,
                "name": sailing.name,
                "area": sailing.area,
                "start": self._format_sailing_date(sailing.start_date),
                "end": self._format_sailing_date(sailing.end_date),
                "co": sailing.co_name,
                "xo": sailing.xo_name,
                "status": sailing.status,
                "personnel_count": personnel.count() - civilian_count,
                "civilians": civilian_data,
                "civilian_count": civilian_count,
                "departments": departments,
            }
        )

    def destroy(self, request, *args, **kwargs):
        sailing = get_object_or_404(Sailing, pk=kwargs["pk"], status="active")
        sailing.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        sailing = get_object_or_404(Sailing, pk=pk, status="active")
        serializer = SailingCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(sailing)
        return Response({"status": "ok"})

    def _get_leave_status(self, personal_number, today, absent_pnos):
        if personal_number not in absent_pnos:
            return "Present"

        leave = LeaveApplication.objects.filter(
            personal_number=personal_number,
            application_status="Approved",
            start_date__lte=today,
            end_date__gte=today,
        ).first()

        return leave.leave_type if leave else OnLeave

    def _get_personnel_row(self, person, status):
        return {
            "source": "personnel",
            "profile_id": person.id,
            "rank": person.rank.name if person.rank else "",
            "name": f"{person.firstname} {person.lastname}".strip(),
            "pno": person.personal_number,
            "dept": person.department.name if person.department else "",
            "desig": (
                person.designation
                or (
                    person.designation_master.designation_name
                    if person.designation_master
                    else ""
                )
            ),
            "status": status,
        }

    def _get_civilian_row(self, civilian):
        pno = civilian.service_no or civilian.ref_id or f"CIV-{civilian.id}"
        dept_label = (civilian.person_type or "civilian").replace(
            "_", " "
        ).title() or "Civilian"

        return {
            "source": "civilian",
            "civilian_id": civilian.id,
            "rank": civilian.rank_snapshot or "",
            "name": civilian.name_snapshot,
            "pno": pno,
            "dept": dept_label,
            "desig": civilian.role,
            "status": "Present",
        }

    def _get_available_personnel(
        self,
        personnel_qs,
        already_pnos,
        today,
        absent_pnos,
    ):
        rows = []

        for person in personnel_qs:
            pno = person.personal_number

            if pno in already_pnos:
                continue

            status = self._get_leave_status(
                pno,
                today,
                absent_pnos,
            )

            rows.append(
                self._get_personnel_row(
                    person,
                    status,
                )
            )

        return rows

    def _get_available_civilians(self, civilian_qs, already_pnos):
        rows = []

        for civilian in civilian_qs:
            pno = civilian.service_no or civilian.ref_id or f"CIV-{civilian.id}"

            if pno in already_pnos:
                continue

            rows.append(self._get_civilian_row(civilian))

        return rows

    @action(detail=True, methods=["get"], url_path="available_personnel")
    def available_personnel(self, request, pk=None):
        """Return personnel and civilians available for a sailing."""
        sailing = self.get_object()

        already_pnos = set(
            sailing.personnel.values_list(
                "pno_snapshot",
                flat=True,
            )
        )

        today = timezone.now().date()
        absent_pnos = _absent_pnos(today, today)

        personnel_qs = CustomUserProfile.objects.filter(
            user_active=True,
            ship_leaving_date__isnull=True,
        ).select_related(
            "rank",
            "department",
            "designation_master",
        )

        civilian_qs = CivilianOfficial.objects.filter(
            is_active=True,
        )

        rows = self._get_available_personnel(
            personnel_qs,
            already_pnos,
            today,
            absent_pnos,
        )

        rows.extend(
            self._get_available_civilians(
                civilian_qs,
                already_pnos,
            )
        )

        return Response({"available": rows})

    def _build_add_personnel_items(self, body):
        items = []

        if body.get("personnel_id"):
            items.append(
                {
                    "source": "personnel",
                    "profile_id": body["personnel_id"],
                }
            )

        if body.get("civilian_id"):
            items.append(
                {
                    "source": "civilian",
                    "civilian_id": body["civilian_id"],
                }
            )

        items.extend(
            {
                "source": "personnel",
                "profile_id": profile_id,
            }
            for profile_id in body.get("personnel_ids", []) or []
        )

        items.extend(
            {
                "source": "civilian",
                "civilian_id": civilian_id,
            }
            for civilian_id in body.get("civilian_ids", []) or []
        )

        return items

    def _get_personnel_status(self, personal_number, today, absent_pnos):
        if personal_number not in absent_pnos:
            return "Present"

        leave = LeaveApplication.objects.filter(
            personal_number=personal_number,
            application_status="Approved",
            start_date__lte=today,
            end_date__gte=today,
        ).first()

        status_value = leave.leave_type if leave else OnLeave

        return (
            status_value if status_value in ("Present", OnLeave, TyDuty) else "Present"
        )

    def _add_sailing_personnel(
        self,
        sailing,
        profile,
        request_user,
        today,
        absent_pnos,
    ):
        status_value = self._get_personnel_status(
            profile.personal_number,
            today,
            absent_pnos,
        )

        SailingPersonnel.objects.create(
            sailing=sailing,
            profile=profile,
            rank_snapshot=profile.rank.name if profile.rank else "",
            name_snapshot=(f"{profile.firstname} {profile.lastname}").strip(),
            pno_snapshot=profile.personal_number,
            dept_snapshot=(profile.department.name if profile.department else ""),
            desig_snapshot=profile.designation or "",
            status_override=status_value,
            created_by=request_user,
        )

    def _add_sailing_civilian(
        self,
        sailing,
        civilian,
        request_user,
    ):
        pno = civilian.service_no or civilian.cid or f"CIV-{civilian.id}"

        SailingPersonnel.objects.create(
            sailing=sailing,
            name_snapshot=civilian.name_snapshot,
            rank_snapshot=civilian.rank_snapshot or "",
            pno_snapshot=pno,
            dept_snapshot=(
                (civilian.person_type or "civilian").replace("_", " ").title()
                or "Civilian"
            ),
            desig_snapshot=civilian.role,
            person_type=civilian.person_type,
            role=civilian.role,
            service_no=civilian.service_no,
            fleet=civilian.fleet,
            ship=civilian.ship,
            cid=civilian.cid,
            contact=civilian.contact,
            remarks=civilian.remarks,
            status_override="Present",
            created_by=request_user,
        )

        return pno

    def _add_personnel_item(
        self,
        sailing,
        item,
        existing_pnos,
        request_user,
        today,
        absent_pnos,
    ):
        source = item.get("source")

        if source == "personnel":
            profile = (
                CustomUserProfile.objects.filter(
                    id=item.get("profile_id"),
                )
                .select_related("rank", "department")
                .first()
            )

            if not profile:
                return False

            pno = profile.personal_number

            if pno in existing_pnos:
                return False

            self._add_sailing_personnel(
                sailing,
                profile,
                request_user,
                today,
                absent_pnos,
            )

            existing_pnos.add(pno)
            return True

        if source == "civilian":
            civilian = CivilianOfficial.objects.filter(
                id=item.get("civilian_id"),
            ).first()

            if not civilian:
                return False

            pno = civilian.service_no or civilian.cid or f"CIV-{civilian.id}"

            if pno in existing_pnos:
                return False

            self._add_sailing_civilian(
                sailing,
                civilian,
                request_user,
            )

            existing_pnos.add(pno)
            return True

        return False

    @action(
        detail=True,
        methods=["post"],
        url_path="add_personnel",
    )
    def add_personnel(self, request, pk=None):
        """Add personnel or civilians to a sailing."""
        sailing = self.get_object()

        if sailing.status == "completed":
            return Response(
                {
                    "status": "error",
                    "message": "Sailing is completed and locked.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        items = self._build_add_personnel_items(request.data)

        today = timezone.now().date()
        absent_pnos = _absent_pnos(today, today)

        existing_pnos = set(
            sailing.personnel.values_list(
                "pno_snapshot",
                flat=True,
            )
        )

        added = 0
        skipped = 0

        for item in items:
            success = self._add_personnel_item(
                sailing=sailing,
                item=item,
                existing_pnos=existing_pnos,
                request_user=request.user.CustomUser_profile,
                today=today,
                absent_pnos=absent_pnos,
            )

            if success:
                added += 1
            else:
                skipped += 1

        return Response(
            {
                "status": "ok",
                "added": added,
                "skipped": skipped,
            }
        )

    def _get_assignment_data(self, personnel, saved):
        assignment = saved.get(personnel.pno_snapshot)

        return {
            "id": personnel.id,
            "pno": personnel.pno_snapshot,
            "name": personnel.name_snapshot,
            "rank": personnel.rank_snapshot,
            "dept": self._get_personnel_department(personnel),
            "desig": personnel.desig_snapshot,
            "w3": assignment.w3 if assignment else "",
            "w2": assignment.w2 if assignment else "",
            "action": assignment.action if assignment else "",
            "defence": assignment.defence if assignment else "",
            "cruising": assignment.cruising if assignment else "",
            "shelter": assignment.shelter if assignment else "",
            "emergency": assignment.emergency if assignment else "",
            "lr": assignment.lr if assignment else "",
            "mess": assignment.mess if assignment else "",
            "blood_group": assignment.blood_group if assignment else "",
            "ssd": assignment.ssd if assignment else "",
            "mess_stn": assignment.mess_stn if assignment else "",
            "section": assignment.section if assignment else "",
            "remarks": assignment.remarks if assignment else "",
        }

    def _get_personnel_department(self, personnel):
        if personnel.dept_snapshot:
            return personnel.dept_snapshot

        if personnel.person_type:
            return personnel.person_type.replace("_", " ").title()

        return "Civilian"

    def _get_assignments(self, sailing):
        personnel = sailing.personnel.all().order_by(
            "dept_snapshot",
            "rank_snapshot",
        )

        saved = {
            assignment.pno: assignment
            for assignment in PersonnelAssignment.objects.filter(
                sailing=sailing,
            )
        }

        return [self._get_assignment_data(person, saved) for person in personnel]

    def _get_assignments_response(self, sailing):
        return {
            "sailing_id": sailing.id,
            "sailing_name": sailing.name,
            "sailing_status": sailing.status,
            "personnel": self._get_assignments(sailing),
        }

    def _save_assignments(self, sailing, request):
        serializer = AssignmentsSaveSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        return serializer.save(sailing)

    @action(detail=True, methods=["get", "post"])
    def assignments(self, request, pk=None):
        """GET/POST assignments for a sailing."""
        sailing = self.get_object()

        if request.method == "GET":
            return Response(self._get_assignments_response(sailing))

        updated = self._save_assignments(
            sailing,
            request,
        )

        return Response(
            {
                "status": "ok",
                "updated": updated,
            }
        )


@extend_schema(tags=["Ship Crew"])
class SailingPersonnelDetailView(APIView):
    """
    PATCH/DELETE sailings/personnel/{sp_id}/ -> replaces
    watch_station_bill_sailing_personnel_update (:1148, already keyed by
    the SailingPersonnel pk as `sp_pk`) and
    watch_station_bill_sailing_personnel_remove (:2239).

    NOTE: legacy's *remove* view was actually keyed by the *sailing* pk plus
    a `identifier` (pno_snapshot) body field to locate the row within it —
    inconsistent with the *update* view next to it, which already used the
    SailingPersonnel row's own pk directly. This endpoint uniformly keys
    both PATCH and DELETE by the SailingPersonnel row's own id (sp_id), per
    this app's endpoint map — an intentional URL redesign for consistency,
    not a straight port of remove's original sailing-pk+identifier scheme.
    The same cascade side effect (deleting the row's PersonnelAssignment)
    is preserved.
    """

    def patch(self, request, sp_id):
        sp = get_object_or_404(SailingPersonnel, pk=sp_id)
        if sp.sailing.status == "completed":
            return Response(
                {"error": "Sailing is completed and locked."},
                status=status.HTTP_403_FORBIDDEN,
            )
        sp.watch_station = request.data.get("watch", sp.watch_station)
        sp.action_station = request.data.get("action", sp.action_station)
        sp.status_override = request.data.get("status", sp.status_override)
        sp.save()
        return Response({"status": "ok"})

    def delete(self, request, sp_id):
        sp = get_object_or_404(SailingPersonnel, pk=sp_id)
        PersonnelAssignment.objects.filter(
            sailing=sp.sailing, pno=sp.pno_snapshot
        ).delete()
        sp.delete()
        return Response({"status": "ok"})


# --------------------------------------------------------------------------
# Watch Station Bill — masters
#
# NOTE on watchbill_ranks_list (crewmanage/views.py:2379): it returns the
# Rank list flagged with `already_classified` against
# SailorRankClassification.rank_name. That's fully derivable client-side by
# combining two endpoints that already exist elsewhere: GET
# /api/user_drf/ranks/ (all ranks) and GET rank-classifications/ (the
# classified rank_name set below) — so no dedicated endpoint is added here,
# consistent with "no need to replicate the string-dispatch mechanism".
# --------------------------------------------------------------------------


@extend_schema(tags=["Ship Crew"])
class ActionStationMasterViewSet(viewsets.ModelViewSet):
    serializer_class = ActionStationMasterSerializer
    queryset = ActionStationMaster.objects.all().order_by("name")


@extend_schema(tags=["Ship Crew"])
class DefenceStationMasterViewSet(viewsets.ModelViewSet):
    serializer_class = DefenceStationMasterSerializer
    queryset = DefenceStationMaster.objects.all().order_by("name")


@extend_schema(tags=["Ship Crew"])
class CruisingStationMasterViewSet(viewsets.ModelViewSet):
    serializer_class = CruisingStationMasterSerializer
    queryset = CruisingStationMaster.objects.all().order_by("name")


@extend_schema(tags=["Ship Crew"])
class ShelterStationMasterViewSet(viewsets.ModelViewSet):
    serializer_class = ShelterStationMasterSerializer
    queryset = ShelterStationMaster.objects.all().order_by("name")


@extend_schema(tags=["Ship Crew"])
class EmergencyStationMasterViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyStationMasterSerializer
    queryset = EmergencyStationMaster.objects.all().order_by("name")


@extend_schema(tags=["Ship Crew"])
class SailorRankClassificationViewSet(viewsets.ModelViewSet):
    serializer_class = SailorRankClassificationSerializer
    queryset = SailorRankClassification.objects.all().order_by("rank_name")
