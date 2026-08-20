"""
Views for hotwork_drf -- class-based only (APIView / ModelViewSet), with
permission_classes set explicitly per view/action via get_permissions(),
mirroring crewmanage_drf/inouttag_drf's own views.py.

See the module docstrings in serializers.py and permissions.py for the
shared RBAC/validation plumbing imported below.
"""

import base64
import json
import os
from datetime import datetime, time, timedelta
from io import BytesIO

import qrcode
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from weasyprint import HTML

from dart.models import InitiateDart
from master.models import Department, Ship, SubDepartment
from users.models import CustomUserProfile

from .models import (
    AddHotwork,
    DayType,
    HotworkHODApproval,
    HotworkProgressActivity,
    HotworkType,
)
from .serializers import (
    HotworkCompleteSerializer,
    HotworkCreateSerializer,
    HotworkDyhodApproveSerializer,
    HotworkHodApproveSerializer,
    HotworkOodApproveSerializer,
    HotworkPauseSerializer,
    HotworkSerializer,
)

# ==========================================================================
# Time-window helpers (pure ports of the same-named module functions in
# Hotwork/views.py -- no DB access, safe to reuse verbatim)
# ==========================================================================

PENDING_APPROVAL_STATUSES = [
    "pending_dyhod",
    "pending_first_hod",
    "pending_hods",
    "pending_ood",
]

HOD = "Head of Department"
HotworkDone = "This hotwork is already completed."


def _profile(user):
    return getattr(user, "user_profile", None)


def _get_hotwork_window_bounds(hotwork):
    """Port of Hotwork/views.py:67."""
    if not hotwork.date_of_hotwork:
        return (None, None)

    tz = timezone.get_current_timezone()
    if hotwork.night_work:
        start_at = timezone.make_aware(
            datetime.combine(hotwork.date_of_hotwork, time(17, 0)), tz
        )
        end_at = timezone.make_aware(
            datetime.combine(hotwork.date_of_hotwork + timedelta(days=1), time(4, 0)),
            tz,
        )
    else:
        start_at = timezone.make_aware(
            datetime.combine(hotwork.date_of_hotwork, time(9, 0)), tz
        )
        end_at = timezone.make_aware(
            datetime.combine(hotwork.date_of_hotwork, time(17, 0)), tz
        )
    return (start_at, end_at)


def _is_hotwork_window_expired(hotwork, now=None):
    """Port of Hotwork/views.py:82."""
    now = now or timezone.localtime(timezone.now())
    _, end_at = _get_hotwork_window_bounds(hotwork)
    if not end_at:
        return False
    if hotwork.night_work:
        return now >= end_at
    return now > end_at


def _auto_complete_paused_hotwork_if_expired(hotwork, now=None):
    """Port of Hotwork/views.py:93 (_auto_complete_paused_hotwork_if_expired)
    -- auto-completes a paused hotwork whose time window has lapsed, writing
    a HotworkProgressActivity row. Called from the same call sites as
    legacy: list/pending_approval/track/report and start.

    BUG FIX (item 2): legacy read is_completed/is_started/is_paused and then
    wrote the auto-complete with no locking at all -- a TOCTOU race where two
    concurrent requests reading the same row (e.g. two callers hitting
    list/pending_approval simultaneously) could both decide to auto-complete
    and double-write a HotworkProgressActivity row. The check-and-set is now
    wrapped in transaction.atomic() + select_for_update() on this specific
    hotwork row so it's serialized against other callers.
    """
    now = now or timezone.localtime(timezone.now())
    if hotwork.is_completed or not hotwork.is_started or not hotwork.is_paused:
        return False
    if not _is_hotwork_window_expired(hotwork, now):
        return False

    changed = False
    with transaction.atomic():
        locked = AddHotwork.objects.select_for_update().get(pk=hotwork.pk)
        if (
            not locked.is_completed
            and locked.is_started
            and locked.is_paused
            and _is_hotwork_window_expired(locked, now)
        ):
            performer = locked.paused_by or locked.started_by
            locked.is_completed = True
            locked.is_paused = False
            locked.completed_by = performer
            locked.completed_at = now
            if not locked.completion_remarks:
                locked.completion_remarks = (
                    "Auto-completed: hotwork time window expired while paused."
                )
            locked.save()

            HotworkProgressActivity.objects.create(
                hotwork=locked,
                action="completed",
                performed_by=performer,
                remarks="Auto-completed: hotwork time window expired while paused.",
            )
            changed = True

    # Reflect the (possibly concurrent) final state onto the caller's own
    # in-memory instance, since every call site keeps using `hotwork`
    # afterwards for display/filtering.
    hotwork.is_completed = locked.is_completed
    hotwork.is_paused = locked.is_paused
    hotwork.completed_by = locked.completed_by
    hotwork.completed_by_id = locked.completed_by_id
    hotwork.completed_at = locked.completed_at
    hotwork.completion_remarks = locked.completion_remarks
    return changed


def _compute_show_actions(hotwork, now):
    """Port of managehotwork's show_actions computation
    (Hotwork/views.py:746-775)."""
    if not hotwork.date_of_hotwork:
        return False

    current_date = now.date()
    current_time = now.time()

    if hotwork.night_work:
        start_time = time(17, 0)
        end_time = time(4, 0)
        next_day = hotwork.date_of_hotwork + timedelta(days=1)
        return (
            current_date == hotwork.date_of_hotwork and current_time >= start_time
        ) or (current_date == next_day and current_time < end_time)

    start_time = time(9, 0)
    end_time = time(17, 0)
    return (
        current_date == hotwork.date_of_hotwork
        and start_time <= current_time <= end_time
    )


def _get_user_hod_approval(hotwork, user_department, is_hod):
    if not (is_hod and user_department):
        return None

    return HotworkHODApproval.objects.filter(
        hotwork=hotwork,
        department=user_department,
    ).first()


def _is_user_dyhod(hotwork, is_dyhod, user_dept_id):
    return (
        is_dyhod
        and hotwork.created_by_id
        and hotwork.created_by.department_id == user_dept_id
    )


def _is_user_hod(is_hod, user_department):
    return is_hod and user_department


def _is_user_ood(hotwork, profile, is_ood):
    return is_ood and hotwork.officer_of_the_day_id == profile.id


def _get_role_approvals(
    hotwork,
    profile,
    is_incharge,
    is_dyhod,
    is_hod,
    is_ood,
    user_department,
    hod_approval,
):
    user_dept_id = getattr(user_department, "id", None)

    return {
        "incharge": (
            is_incharge
            and hotwork.hotwork_incharge_id == profile.id
            and hotwork.incharge_approved
        ),
        "dyhod": (
            _is_user_dyhod(
                hotwork,
                is_dyhod,
                user_dept_id,
            )
            and hotwork.dyhod_approved
        ),
        "hod": (
            _is_user_hod(
                is_hod,
                user_department,
            )
            and hod_approval
            and hod_approval.approved
        ),
        "ood": (
            _is_user_ood(
                hotwork,
                profile,
                is_ood,
            )
            and hotwork.ood_approved
        ),
    }


def _get_pending_role(
    hotwork,
    profile,
    is_dyhod,
    is_hod,
    is_ood,
    user_department,
):
    user_dept_id = getattr(user_department, "id", None)

    if hotwork.approval_status == "pending_dyhod":
        return (
            "dyhod"
            if _is_user_dyhod(
                hotwork,
                is_dyhod,
                user_dept_id,
            )
            else None
        )

    if hotwork.approval_status == "pending_hods":
        return (
            "hod"
            if _is_user_hod(
                is_hod,
                user_department,
            )
            else None
        )

    if hotwork.approval_status == "pending_ood":
        return (
            "ood"
            if _is_user_ood(
                hotwork,
                profile,
                is_ood,
            )
            else None
        )

    return None


def _compute_user_already_approved(
    hotwork,
    profile,
    is_incharge,
    is_dyhod,
    is_hod,
    is_ood,
    user_department,
):
    """Return whether the user has already approved this hotwork."""

    hod_approval = _get_user_hod_approval(
        hotwork,
        user_department,
        is_hod,
    )

    approvals = _get_role_approvals(
        hotwork,
        profile,
        is_incharge,
        is_dyhod,
        is_hod,
        is_ood,
        user_department,
        hod_approval,
    )

    pending_role = _get_pending_role(
        hotwork,
        profile,
        is_dyhod,
        is_hod,
        is_ood,
        user_department,
    )

    if pending_role:
        return approvals[pending_role]

    return any(approvals.values())


########################################################


# --------------------------------------------------------------------------
# Certificate PDF helpers (ports of the same-named module functions in
# Hotwork/views.py)
# --------------------------------------------------------------------------


def _format_user_with_rank(user_profile):
    """Port of Hotwork/views.py:1441."""
    if not user_profile:
        return "N/A"
    return (
        " ".join(
            filter(
                None,
                [
                    user_profile.rank.name
                    if getattr(user_profile, "rank", None)
                    else "",
                    (user_profile.firstname or "").strip(),
                    (user_profile.lastname or "").strip(),
                ],
            )
        )
        or "N/A"
    )


def _format_datetime_local(value, fmt="%d %b %Y %H:%M"):
    """Port of Hotwork/views.py:1452."""
    if not value:
        return "N/A"
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return timezone.localtime(value).strftime(fmt)


def generate_hotwork_qr_code(
    hotwork, hod_engineering=None, hod_electrical=None, hod_nbcd=None
):
    """Port of Hotwork/views.py:1576 (generate_hotwork_qr_code)."""
    qr_payload = {
        "hotwork_id": hotwork.id,
        "hotwork_code": hotwork.hotwork_code,
        "date_of_hotwork": hotwork.date_of_hotwork.isoformat()
        if hotwork.date_of_hotwork
        else None,
        "location_of_hotwork": hotwork.location_of_hotwork,
        "type_of_hotwork": hotwork.type_of_hotwork,
        "night_work": hotwork.night_work,
        "holiday_or_working_day": hotwork.holiday_or_working_day,
        "approval_status": hotwork.approval_status,
        "approvals": {
            "dyhod": {
                "approved": bool(hotwork.dyhod_approved),
                "approved_by": _format_user_with_rank(hotwork.dyhod_approved_by),
                "approved_at": _format_datetime_local(hotwork.dyhod_approved_at),
            },
            "engineering_hod": {
                "approved": bool(hod_engineering and hod_engineering.approved),
                "approved_by": _format_user_with_rank(
                    hod_engineering.approved_by if hod_engineering else None
                ),
                "approved_at": _format_datetime_local(
                    hod_engineering.approved_at if hod_engineering else None
                ),
            },
            "electrical_hod": {
                "approved": bool(hod_electrical and hod_electrical.approved),
                "approved_by": _format_user_with_rank(
                    hod_electrical.approved_by if hod_electrical else None
                ),
                "approved_at": _format_datetime_local(
                    hod_electrical.approved_at if hod_electrical else None
                ),
            },
            "nbcd_hod": {
                "approved": bool(hod_nbcd and hod_nbcd.approved),
                "approved_by": _format_user_with_rank(
                    hod_nbcd.approved_by if hod_nbcd else None
                ),
                "approved_at": _format_datetime_local(
                    hod_nbcd.approved_at if hod_nbcd else None
                ),
            },
            "ood": {
                "approved": bool(hotwork.ood_approved),
                "approved_by": _format_user_with_rank(hotwork.ood_approved_by),
                "approved_at": _format_datetime_local(hotwork.ood_approved_at),
            },
        },
    }

    qr_data = json.dumps(qr_payload, ensure_ascii=False)
    qr_image = qrcode.make(qr_data)
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ==========================================================================
# Dashboard
# ==========================================================================


@extend_schema(tags=["Hotwork"])
class DashboardView(APIView):
    """GET dashboard/ -- reproduces hotworkhome's aggregate KPI/chart data
    (Hotwork/views.py:117), not a page shell: today/scheduled/in-progress/
    ready-to-start/awaiting-approval/completed-today counts, weekly_data
    (last 10 days), progress_data (pie breakdown), history_data (last ~12
    months), and role flags."""

    def get(self, request):
        today = timezone.localtime(timezone.now()).date()
        first_day_of_month = today.replace(day=1)
        last_10_days_start = today - timedelta(days=9)

        scheduled_today = AddHotwork.objects.filter(
            date_of_hotwork=today, approval_status="approved"
        ).count()
        hotwork_in_progress_today = AddHotwork.objects.filter(
            date_of_hotwork=today, approval_status="approved", is_completed=False
        ).count()
        ready_to_start_today = AddHotwork.objects.filter(
            date_of_hotwork=today,
            approval_status="approved",
            is_started=False,
            is_completed=False,
        ).count()
        awaiting_approval_today = AddHotwork.objects.filter(
            date_of_hotwork=today, approval_status__in=PENDING_APPROVAL_STATUSES
        ).count()
        completed_today = AddHotwork.objects.filter(
            is_completed=True, completed_at__date=today
        ).count()

        weekly_data = []
        for i in range(10):
            chart_date = last_10_days_start + timedelta(days=i)
            initiated_count = AddHotwork.objects.filter(
                date_of_hotwork=chart_date,
                approval_status__in=PENDING_APPROVAL_STATUSES,
            ).count()
            ready_count = AddHotwork.objects.filter(
                date_of_hotwork=chart_date, approval_status="approved", is_started=False
            ).count()
            completed_count = AddHotwork.objects.filter(
                completed_at__date=chart_date, is_completed=True
            ).count()
            weekly_data.append(
                {
                    "date": chart_date.strftime("%d %b %y"),
                    "initiated": initiated_count,
                    "ready": ready_count,
                    "completed": completed_count,
                }
            )

        initiated_total = AddHotwork.objects.filter(
            date_of_hotwork=today, approval_status__in=PENDING_APPROVAL_STATUSES
        ).count()
        ready_total = AddHotwork.objects.filter(
            date_of_hotwork=today,
            approval_status="approved",
            is_started=False,
            is_completed=False,
        ).count()
        completed_total = AddHotwork.objects.filter(
            completed_at__date=today, is_completed=True
        ).count()
        paused_total = AddHotwork.objects.filter(
            date_of_hotwork=today, is_paused=True, is_completed=False
        ).count()

        progress_data = [
            {"category": "Initiated", "value": initiated_total, "color": "#f39c12"},
            {"category": "Ready", "value": ready_total, "color": "#e17055"},
            {"category": "Paused", "value": paused_total, "color": "#d63031"},
            {"category": "Completed", "value": completed_total, "color": "#0984e3"},
        ]

        history_start_date = first_day_of_month
        for _ in range(11):
            history_start_date = (history_start_date - timedelta(days=1)).replace(day=1)

        ready_counts = {
            item["date_of_hotwork"]: item["total"]
            for item in AddHotwork.objects.filter(
                date_of_hotwork__gte=history_start_date,
                approval_status="approved",
                is_started=False,
            )
            .values("date_of_hotwork")
            .annotate(total=Count("id"))
        }
        in_progress_counts = {
            item["date_of_hotwork"]: item["total"]
            for item in AddHotwork.objects.filter(
                date_of_hotwork__gte=history_start_date,
                is_started=True,
                is_completed=False,
            )
            .values("date_of_hotwork")
            .annotate(total=Count("id"))
        }
        completed_counts = {
            item["completed_at__date"]: item["total"]
            for item in AddHotwork.objects.filter(
                completed_at__date__gte=history_start_date, is_completed=True
            )
            .values("completed_at__date")
            .annotate(total=Count("id"))
        }
        all_history_dates = sorted(
            set(ready_counts) | set(in_progress_counts) | set(completed_counts)
        )
        history_data = [
            {
                "date": chart_date.strftime("%Y-%m-%d"),
                "ready": ready_counts.get(chart_date, 0),
                "in_progress": in_progress_counts.get(chart_date, 0),
                "completed": completed_counts.get(chart_date, 0),
            }
            for chart_date in all_history_dates
        ]

        pending_user_registrations_count = CustomUserProfile.objects.filter(
            is_role=False
        ).count()

        payload = {
            "scheduled_today": scheduled_today,
            "hotwork_in_progress_today": hotwork_in_progress_today,
            "ready_to_start_today": ready_to_start_today,
            "awaiting_approval_today": awaiting_approval_today,
            "completed_today": completed_today,
            "weekly_data": weekly_data,
            "progress_data": progress_data,
            "history_data": history_data,
            "pending_user_registrations_count": pending_user_registrations_count,
            "today_date": today.strftime("%Y-%m-%d"),
        }
        return Response(payload)


# ==========================================================================
# Hotwork lifecycle
# ==========================================================================


@extend_schema(tags=["Hotwork"])
class HotworkViewSet(viewsets.ModelViewSet):
    """
    Endpoint map (legacy originals in Hotwork/views.py):
      list                    -> managehotwork (:667)
      create                  -> addhotwork's POST branch (:798-1020)
      retrieve                -> NEW (no legacy equivalent) -- gated by just
                                  IsAccountActive, matching the legacy
                                  baseline of zero read-side auth.
      form_meta (GET)         -> addhotwork's GET branch (:798-861)
      inbox (GET)             -> hotworks awaiting the caller's approval
      outbox (GET)            -> hotworks created by the caller
      pending_approval (GET)  -> hotworkapproval (:323)
      track (GET)             -> trackhotwork (:540)
      report (GET)            -> reporthotwork (:627)
      dyhod_approve (POST)    -> dyhod_approve_hotwork (:1072)
      hod_approve (POST)      -> hod_approve_hotwork (:1140)
      ood_approve (POST)      -> ood_approve_hotwork (:1236)
      start (POST)            -> start_hotwork (:1326) -- now gated by
                                  CanOperateLifecycle (tightening, see
                                  permissions.py)
      pause (POST)            -> pause_hotwork (:1366) -- same tightening
      complete (POST)         -> complete_hotwork (:1401) -- same tightening
      print_certificate (GET) -> print_hotwork_certificate (:1462) -- now
                                  gated by CanPrintCertificate (tightening)

    incharge_approve_hotwork (dead stub) and usermasterhotwork (non-
    functional placeholder) are intentionally NOT ported (confirmed
    excluded).
    """

    http_method_names = ("get", "post", "head", "options")

    def get_serializer_class(self):
        if self.action == "create":
            return HotworkCreateSerializer
        return HotworkSerializer

    def get_queryset(self):
        return (
            AddHotwork.objects.select_related(
                "sub_department",
                "created_by",
                "created_by__ship",
                "created_by__department",
                "hotwork_incharge",
                "officer_of_the_day",
                "dyhod_approved_by",
                "incharge_approved_by",
                "ood_approved_by",
                "started_by",
                "paused_by",
                "completed_by",
            )
            .prefetch_related("hod_approvals__department", "hod_approvals__approved_by")
            .order_by("-created_at")
            .distinct()
        )

    # ------------------------------------------------------------------
    # POST hotworks/ -- addhotwork's POST branch
    # ------------------------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = HotworkCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        hotwork = serializer.save()
        output = HotworkSerializer(hotwork, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # GET hotworks/ -- managehotwork (Hotwork/views.py:667)
    # ------------------------------------------------------------------
    def list(self, request, *args, **kwargs):
        profile = _profile(request.user)
        if profile is None:
            return Response([])

        user_department = profile.department

        query = (
            Q(created_by=profile)
            | Q(hotwork_incharge=profile)
            | Q(officer_of_the_day=profile)
        )

        # Night/Holiday hotworks are OOD-only flow and should not appear
        # in the HOD lane.
        hod_applicable_query = Q(night_work=False) & ~Q(
            holiday_or_working_day="holiday"
        )
        hod_visibility_query = Q(
            hod_approvals__department=user_department,
            hod_approvals__approved=False,
            approval_status__in=["pending_first_hod", "pending_hods"],
        ) | Q(hod_approvals__department=user_department, hod_approvals__approved=True)
        query |= hod_applicable_query & hod_visibility_query

        hotworks = self.get_queryset().filter(query).order_by("-created_at").distinct()
        hotworks = hotworks.filter(is_completed=False)

        now = timezone.localtime(timezone.now())
        visible = []
        for hotwork in hotworks:
            _auto_complete_paused_hotwork_if_expired(hotwork, now)
            if hotwork.is_completed:
                continue
            if _is_hotwork_window_expired(hotwork, now):
                continue
            # NOTE: this second expired check is redundant with the one
            # immediately above in the legacy view too (Hotwork/
            # views.py:734-744) -- kept as a literal port rather than
            # simplified away, since it's provably a no-op, not a bug.
            if (
                hotwork.approval_status == "approved"
                and not hotwork.is_started
                and _is_hotwork_window_expired(hotwork, now)
            ):
                continue

            hotwork.show_actions = _compute_show_actions(hotwork, now)
            visible.append(hotwork)

        serializer = self.get_serializer(visible, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # GET hotworks/form_meta/ -- addhotwork's GET branch
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="form_meta")
    def form_meta(self, request):
        profile = _profile(request.user)
        department_obj = getattr(profile, "department", None) if profile else None

        subdepartments = (
            SubDepartment.objects.filter(department_name=department_obj).order_by("id")
            if department_obj
            else SubDepartment.objects.none()
        )
        previous_hotworks = list(
            AddHotwork.objects.values_list("hotwork_code", flat=True)
        )

        hod_name = ""
        if department_obj:
            hod = CustomUserProfile.objects.filter(
                department=department_obj,
                role_master__role_name=HOD,
                user_active=True,
            ).first()
            if hod:
                hod_name = f"{hod.rank.name if hod.rank else ''} {hod.firstname} {hod.lastname}".strip()

        ood_users = (
            CustomUserProfile.objects.filter(user_active=True, is_ood=True)
            .select_related("rank")
            .order_by("rank__name", "firstname")
        )

        dart_numbers = list(
            InitiateDart.objects.open().values_list("pk", "dart_number")
        )

        return Response(
            {
                "subdepartments": [
                    {"id": s.id, "name": s.name} for s in subdepartments
                ],
                "previous_hotworks": previous_hotworks,
                "hod_name": hod_name,
                "ood_users": [
                    {
                        "id": u.id,
                        "rank": u.rank.name if u.rank else "",
                        "firstname": u.firstname,
                        "lastname": u.lastname,
                    }
                    for u in ood_users
                ],
                "dart_numbers": dart_numbers,
                "type_of_hotwork_choices": [
                    {"value": value, "label": label}
                    for value, label in HotworkType.choices
                ],
                "holiday_or_working_day_choices": [
                    {"value": value, "label": label} for value, label in DayType.choices
                ],
            }
        )

    # ------------------------------------------------------------------
    # GET hotworks/pending_approval/ -- hotworkapproval (Hotwork/views.py:323)
    # ------------------------------------------------------------------
    def _get_pending_approval_context(self, profile):
        """Return the user's approval-role context."""
        user_department = profile.department

        return {
            "is_incharge": self._has_incharge_hotworks(profile),
            "is_ood": self._has_ood_hotworks(profile),
            "user_department": user_department,
        }

    def _has_incharge_hotworks(self, profile):
        return (
            self.get_queryset()
            .filter(
                hotwork_incharge=profile,
            )
            .exists()
        )

    def _has_ood_hotworks(self, profile):
        return (
            self.get_queryset()
            .filter(
                officer_of_the_day=profile,
            )
            .filter(
                Q(approval_status="pending_ood") | Q(ood_approved=True),
            )
            .exists()
        )

    def _get_incharge_hotworks(self, profile):
        return (
            self.get_queryset()
            .filter(
                hotwork_incharge=profile,
            )
            .order_by("-created_at")
        )

    def _get_ood_hotworks(self, profile):
        return (
            self.get_queryset()
            .filter(officer_of_the_day=profile)
            .filter(Q(approval_status="pending_ood") | Q(ood_approved=True))
            .order_by("-created_at")
        )

    def _get_dyhod_hotworks(self, profile, user_department):
        return (
            self.get_queryset()
            .filter(created_by__department=user_department)
            .filter(Q(approval_status="pending_dyhod") | Q(dyhod_approved=True))
            .order_by("-created_at")
        )

    def _get_hod_hotworks(self, user_department):
        applicable_query = Q(night_work=False) & ~Q(holiday_or_working_day="holiday")

        visibility_query = Q(
            hod_approvals__department=user_department,
            hod_approvals__approved=False,
            approval_status__in=[
                "pending_first_hod",
                "pending_hods",
            ],
        ) | Q(
            hod_approvals__department=user_department,
            hod_approvals__approved=True,
        )

        return (
            self.get_queryset()
            .filter(applicable_query & visibility_query)
            .order_by("-created_at")
        )

    # ------------------------------------------------------------------
    # GET hotworks/inbox/ and hotworks/outbox/
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"])
    def inbox(self, request):
        """Return hotworks for which the caller is the current approver.

        A hotwork enters an inbox only at its active approval stage: a
        department officer reviews work raised by their department, an HOD
        reviews their department's outstanding approval row, and the assigned
        OOD performs the final review.  Completed, rejected, and already
        approved records therefore never appear here.
        """
        profile = _profile(request.user)
        if profile is None:
            return Response([])

        department = profile.department
        query = Q(officer_of_the_day=profile, approval_status="pending_ood")

        if department:
            query |= Q(
                created_by__department=department,
                approval_status="pending_dyhod",
            )
            query |= Q(
                hod_approvals__department=department,
                hod_approvals__approved=False,
                approval_status__in=["pending_first_hod", "pending_hods"],
            )

        hotworks = self.get_queryset().filter(query).order_by("-created_at").distinct()
        return Response(self.get_serializer(hotworks, many=True).data)

    @action(detail=False, methods=["get"])
    def outbox(self, request):
        """Return all hotworks raised by the authenticated user."""
        profile = _profile(request.user)
        if profile is None:
            return Response([])

        hotworks = (
            self.get_queryset().filter(created_by=profile).order_by("-created_at")
        )
        return Response(self.get_serializer(hotworks, many=True).data)

    # ------------------------------------------------------------------
    # GET hotworks/track/ -- trackhotwork (Hotwork/views.py:540)
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="track")
    def track(self, request):
        """Despite the generic name, legacy specifically surfaces only
        EXPIRED hotworks related to the caller -- preserved exactly."""
        profile = _profile(request.user)
        if profile is None:
            return Response([])
        # NOTE: trackhotwork's own is_hod check does NOT apply the
        # is_excluded_hod carve-out (unlike managehotwork/hotworkapproval,
        # both of which use perms.is_hod_profile) -- ported faithfully as a
        # plain role-name check, matching Hotwork/views.py:544-545 exactly.
        # This is a genuine legacy inconsistency, not something this
        # conversion was asked to fix.
        role_name = getattr(getattr(profile, "role_master", None), "role_name", None)
        is_hod_role = role_name == HOD

        query = (
            Q(created_by=profile)
            | Q(hotwork_incharge=profile)
            | Q(officer_of_the_day=profile)
            | Q(started_by=profile)
            | Q(paused_by=profile)
            | Q(completed_by=profile)
            | Q(dyhod_approved_by=profile)
            | Q(ood_approved_by=profile)
            | Q(hod_approvals__approved_by=profile)
        )
        if is_hod_role:
            query |= (
                Q(approval_status__in=["pending_first_hod", "pending_hods", "approved"])
                | Q(dyhod_approved=True)
                | Q(is_completed=True)
            )

        hotworks = self.get_queryset().filter(query).order_by("-created_at").distinct()

        now = timezone.localtime(timezone.now())
        expired = []
        for hotwork in hotworks:
            _auto_complete_paused_hotwork_if_expired(hotwork, now)
            if not _is_hotwork_window_expired(hotwork, now):
                continue
            expired.append(hotwork)

        serializer = self.get_serializer(expired, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # GET hotworks/report/ -- reporthotwork (Hotwork/views.py:627)
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"], url_path="report")
    def report(self, request):
        profile = _profile(request.user)
        if profile is None:
            return Response([])

        # Same note as track(): reporthotwork's is_hod check also has no
        # is_excluded_hod carve-out in the legacy view (Hotwork/
        # views.py:631-632) -- ported as-is.

        hotworks = (
            self.get_queryset()
            .filter(Q(dyhod_approved=True) | Q(created_by=profile))
            .order_by("-created_at")
        )

        serializer = self.get_serializer(hotworks, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # POST hotworks/{id}/dyhod_approve/ -- dyhod_approve_hotwork (:1072)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="dyhod_approve")
    def dyhod_approve(self, request, pk=None):
        hotwork = self.get_object()
        profile = _profile(request.user)

        if hotwork.approval_status != "pending_dyhod":
            raise ValidationError(
                "This hotwork is not pending Department Officer approval."
            )

        serializer = HotworkDyhodApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action_value = serializer.validated_data["action"]

        if action_value == "approve":
            hotwork.dyhod_approved = True
            hotwork.dyhod_approved_by = profile
            hotwork.dyhod_approved_at = timezone.now()

            if hotwork.night_work or hotwork.holiday_or_working_day == "holiday":
                hotwork.approval_status = "pending_ood"
                hotwork.save()
            else:
                hotwork.approval_status = "pending_hods"
                hotwork.save()

                department = Department.objects.all()
                if (
                    department
                    and CustomUserProfile.objects.filter(
                        department=department,
                        role_master__role_name=HOD,
                        user_active=True,
                    ).exists()
                ):
                    HotworkHODApproval.objects.get_or_create(
                        hotwork=hotwork, department=department
                    )
                hotwork.check_all_hods_approved()
        else:
            hotwork.approval_status = "rejected"
            hotwork.save()

        return Response(
            HotworkSerializer(hotwork, context=self.get_serializer_context()).data
        )

    # ------------------------------------------------------------------
    # POST hotworks/{id}/hod_approve/ -- hod_approve_hotwork (:1140)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="hod_approve")
    def hod_approve(self, request, pk=None):
        hotwork = self.get_object()
        profile = _profile(request.user)

        if hotwork.approval_status not in ("pending_first_hod", "pending_hods"):
            raise ValidationError("This hotwork is not pending HOD approval.")

        hod_approval, _created = HotworkHODApproval.objects.get_or_create(
            hotwork=hotwork, department=profile.department
        )
        if hod_approval.approved:
            raise ValidationError("You have already approved this hotwork.")

        serializer = HotworkHodApproveSerializer(
            data=request.data, context={"dept_id": profile.department_id}
        )
        serializer.is_valid(raise_exception=True)
        action_value = serializer.validated_data["action"]

        if action_value == "approve":
            hod_approval.approved = True
            hod_approval.approved_by = profile
            hod_approval.approved_at = timezone.now()
            serializer.apply_to_approval(hod_approval, profile.department_id)
            hod_approval.save()
            hotwork.check_all_hods_approved()
        else:
            hotwork.approval_status = "rejected"
            # IMPROVEMENT (additive, not a change to the legacy aggregate-
            # status semantics): legacy's reject branch saved hod_approval
            # without recording who rejected it or when (Hotwork/
            # views.py:1227-1230, `hod_approval.save()` with no field
            # changes). We record approved_by/approved_at here too
            # (approved itself stays False) so the per-department row shows
            # a reject trace -- this does not touch how
            # AddHotwork.approval_status itself is set.
            hod_approval.approved_by = profile
            hod_approval.approved_at = timezone.now()
            hod_approval.save()
            hotwork.save()

        return Response(
            HotworkSerializer(hotwork, context=self.get_serializer_context()).data
        )

    # ------------------------------------------------------------------
    # POST hotworks/{id}/ood_approve/ -- ood_approve_hotwork (:1236)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="ood_approve")
    def ood_approve(self, request, pk=None):
        hotwork = self.get_object()
        profile = _profile(request.user)

        if hotwork.approval_status != "pending_ood":
            raise ValidationError(
                "This hotwork is not pending Officer of the Day approval."
            )

        is_night_or_holiday = (
            hotwork.night_work or hotwork.holiday_or_working_day == "holiday"
        )
        serializer = HotworkOodApproveSerializer(
            data=request.data, context={"apply_checklist": is_night_or_holiday}
        )
        serializer.is_valid(raise_exception=True)
        action_value = serializer.validated_data["action"]

        if action_value == "approve":
            if is_night_or_holiday:
                department = Department.objects.all().first()
                if (
                    department
                    and CustomUserProfile.objects.filter(
                        department=department,
                        role_master__role_name=HOD,
                        user_active=True,
                    ).exists()
                ):
                    hod_approval, _created = HotworkHODApproval.objects.get_or_create(
                        hotwork=hotwork, department=department
                    )
                    hod_approval.approved = True
                    hod_approval.approved_by = profile
                    hod_approval.approved_at = timezone.now()
                    serializer.apply_to_approval(hod_approval)
                    hod_approval.save()

            hotwork.ood_approved = True
            hotwork.ood_approved_by = profile
            hotwork.ood_approved_at = timezone.now()
            hotwork.approval_status = "approved"
            hotwork.save()
        else:
            hotwork.approval_status = "rejected"
            hotwork.save()

        return Response(
            HotworkSerializer(hotwork, context=self.get_serializer_context()).data
        )

    # ------------------------------------------------------------------
    # POST hotworks/{id}/start/ -- start_hotwork (:1326)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        hotwork = self.get_object()
        profile = _profile(request.user)

        _auto_complete_paused_hotwork_if_expired(hotwork)

        if not hotwork.ood_approved:
            raise ValidationError(
                "Hotwork cannot be started until OOD approval is completed."
            )
        if hotwork.is_completed:
            raise ValidationError(HotworkDone)
        if not hotwork.is_started and _is_hotwork_window_expired(hotwork):
            raise ValidationError(
                "Hotwork time window has expired. It cannot be started now."
            )

        action_label = "resumed" if hotwork.is_started else "started"
        hotwork.is_started = True
        hotwork.is_paused = False
        if not hotwork.started_by:
            hotwork.started_by = profile
            hotwork.started_at = timezone.now()
        hotwork.save()

        HotworkProgressActivity.objects.create(
            hotwork=hotwork,
            action=action_label,
            performed_by=profile,
            remarks=(
                f"Hotwork {action_label} by "
                f"{profile.rank.name if profile.rank else ''} {profile.firstname} {profile.lastname}"
            ),
        )

        return Response(
            {
                "success": True,
                "message": f"Hotwork {hotwork.hotwork_code} has been {action_label}.",
                "state": "pause",
            }
        )

    # ------------------------------------------------------------------
    # POST hotworks/{id}/pause/ -- pause_hotwork (:1366)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        hotwork = self.get_object()
        profile = _profile(request.user)

        if not hotwork.is_started:
            raise ValidationError("Hotwork must be started before it can be paused.")
        if hotwork.is_completed:
            raise ValidationError(HotworkDone)

        serializer = HotworkPauseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pause_reason = serializer.validated_data["pause_reason"]

        hotwork.is_paused = True
        hotwork.paused_by = profile
        hotwork.paused_at = timezone.now()
        hotwork.pause_reason = pause_reason
        hotwork.save()

        HotworkProgressActivity.objects.create(
            hotwork=hotwork, action="paused", performed_by=profile, remarks=pause_reason
        )

        return Response(
            {
                "success": True,
                "message": f"Hotwork {hotwork.hotwork_code} has been paused.",
            }
        )

    # ------------------------------------------------------------------
    # POST hotworks/{id}/complete/ -- complete_hotwork (:1401)
    # ------------------------------------------------------------------
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        hotwork = self.get_object()
        profile = _profile(request.user)

        if not hotwork.is_started:
            raise ValidationError("Hotwork must be started before it can be completed.")
        if hotwork.is_completed:
            raise ValidationError(HotworkDone)
        # NOTE: legacy explicitly allows completing while paused (its
        # is_paused guard is commented out at Hotwork/views.py:1414-1415) --
        # deliberately not reproduced here (bug-fix item 5's counterpart:
        # don't add a guard back that legacy itself removed).

        serializer = HotworkCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        completion_remarks = serializer.validated_data.get("completion_remarks", "")

        hotwork.is_completed = True
        hotwork.completed_by = profile
        hotwork.completed_at = timezone.now()
        hotwork.completion_remarks = completion_remarks
        hotwork.save()

        HotworkProgressActivity.objects.create(
            hotwork=hotwork,
            action="completed",
            performed_by=profile,
            remarks=completion_remarks
            or f"Hotwork completed by {profile.rank.name if profile.rank else ''} {profile.firstname} {profile.lastname}",
        )
        # BUG FIX (item 5): legacy had unreachable dead code after its
        # `return JsonResponse(...)` here (Hotwork/views.py:1437-1438) --
        # not reproduced.
        return Response(
            {
                "success": True,
                "message": f"Hotwork {hotwork.hotwork_code} has been marked as complete.",
            }
        )

    # ------------------------------------------------------------------
    # GET hotworks/{id}/print_certificate/ -- print_hotwork_certificate (:1462)
    # ------------------------------------------------------------------
    def _get_hotwork_ship(self, hotwork):
        default_ship = Ship.objects.filter(id=1).first()

        if hotwork.created_by and hotwork.created_by.ship:
            return hotwork.created_by.ship

        return default_ship

    def _get_hod_approvals(self, hotwork):
        return {
            "engineering": hotwork.hod_approvals.filter(department_id=2).first(),
            "electrical": hotwork.hod_approvals.filter(department_id=3).first(),
            "nbcd": hotwork.hod_approvals.filter(department_id=5).first(),
        }

    def _build_approval_detail(self, role, approved, approved_by, approved_at):
        return {
            "role": role,
            "status": "Approved" if approved else "Pending",
            "approved_by": _format_user_with_rank(approved_by),
            "approved_at": _format_datetime_local(approved_at),
        }

    def _get_approval_details(
        self,
        hotwork,
        hod_engineering,
        hod_electrical,
        hod_nbcd,
    ):
        return [
            self._build_approval_detail(
                "Department Officer (DY HOD)",
                hotwork.dyhod_approved,
                hotwork.dyhod_approved_by,
                hotwork.dyhod_approved_at,
            ),
            self._build_approval_detail(
                "Engineering HOD",
                hod_engineering.approved if hod_engineering else False,
                hod_engineering.approved_by if hod_engineering else None,
                hod_engineering.approved_at if hod_engineering else None,
            ),
            self._build_approval_detail(
                "Electrical HOD",
                hod_electrical.approved if hod_electrical else False,
                hod_electrical.approved_by if hod_electrical else None,
                hod_electrical.approved_at if hod_electrical else None,
            ),
            self._build_approval_detail(
                "NBCD HOD",
                hod_nbcd.approved if hod_nbcd else False,
                hod_nbcd.approved_by if hod_nbcd else None,
                hod_nbcd.approved_at if hod_nbcd else None,
            ),
            self._build_approval_detail(
                "Officer of the Day",
                hotwork.ood_approved,
                hotwork.ood_approved_by,
                hotwork.ood_approved_at,
            ),
        ]

    def _build_hotwork_certificate_context(
        self,
        hotwork,
        ship,
        approvals,
        request,
    ):
        next_day = (
            hotwork.date_of_hotwork + timedelta(days=1)
            if hotwork.date_of_hotwork
            else None
        )

        static_root = getattr(settings, "STATIC_ROOT", None) or os.path.join(
            settings.BASE_DIR, "static"
        )

        hotwork_qr_code_base64 = generate_hotwork_qr_code(
            hotwork,
            approvals["engineering"],
            approvals["electrical"],
            approvals["nbcd"],
        )

        return {
            "hotwork": hotwork,
            "ship": ship,
            "hod_engineering": approvals["engineering"],
            "hod_electrical": approvals["electrical"],
            "hod_nbcd": approvals["nbcd"],
            "approval_details": self._get_approval_details(
                hotwork,
                approvals["engineering"],
                approvals["electrical"],
                approvals["nbcd"],
            ),
            "hotwork_qr_code_base64": hotwork_qr_code_base64,
            "night_work": hotwork.night_work,
            "STATIC_ROOT": static_root,
            "next_day": next_day,
        }

    @action(detail=True, methods=["get"], url_path="print_certificate")
    def print_certificate(self, request, pk=None):
        """Generate and return the hotwork certificate PDF."""
        hotwork = self.get_object()

        ship = self._get_hotwork_ship(hotwork)
        approvals = self._get_hod_approvals(hotwork)

        context = self._build_hotwork_certificate_context(
            hotwork,
            ship,
            approvals,
            request,
        )

        html_string = render_to_string(
            "hotwork_certificate_pdf.html",
            context,
            request=request,
        )

        base_url = request.build_absolute_uri("/")[:-1]
        pdf_file = HTML(
            string=html_string,
            base_url=base_url,
        ).write_pdf()

        response = HttpResponse(
            pdf_file,
            content_type="application/pdf",
        )
        response["Content-Disposition"] = (
            f'inline; filename="Hotwork_Certificate_{hotwork.hotwork_code}.pdf"'
        )

        return response
