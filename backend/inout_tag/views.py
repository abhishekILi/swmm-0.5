from datetime import timedelta

from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import (
    extend_schema,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from weasyprint import HTML

from master.models import Department
from master.utils import get_this_ship
from sfd.models import ShipEquipment
from users.models import CustomUserProfile

from .models import TagIn, TagInApproval, TagOut
from .serializers import (
    HistorySerializer,
    TagInApprovalActionSerializer,
    TagInSerializer,
    TagOutApprovalActionSerializer,
    TagOutSerializer,
)

# Fields that only apply to one TAG_OUT_REASON_CHOICES branch. addtagout only
# ever set the branch matching the submitted tagout_reason; the others were
# simply never assigned (left at their model default of None). Reproduced
# here so a client can't smuggle e.g. `repair_ra_number` onto a
# 'ty_loan_rtlapp' tagout.
_REASON_ONLY_FIELDS = {
    "ty_loan_rtlapp": [
        "ty_loan_ship",
        "ty_authority",
        "ty_item_taken_by",
        "ty_additional_items",
    ],
    "survey_and_demand": ["survery_demand_authority"],
    "repair_or_overhauling": [
        "repair_ra_number",
        "repair_landed_details",
        "repair_item_taken_by",
        "repair_additional_items",
    ],
    "aber_replacement": [
        "aber_authority",
        "replacement_item",
        "estimated_bom_arrival_date",
    ],
}
_ALL_REASON_FIELDS = {
    field for fields in _REASON_ONLY_FIELDS.values() for field in fields
}

User404 = "User profile not found. Contact administrator."

HOD = "Head of Department"


def _is_co_or_ship_admin(user, profile):
    """CO and Ship Admin are the first approvers for a Tag In request."""
    role_name = getattr(getattr(profile, "role_master", None), "role_name", "")
    designation = (getattr(profile, "designation", "") or "").strip()
    return (
        user.is_staff
        or role_name.strip().casefold() in {"co", "shipadmin", "ship admin"}
        or designation.casefold() == "co"
    )


def _is_hod(profile):
    designation = (getattr(profile, "designation", "") or "").strip().casefold()
    print(designation)
    return designation in {"hod", "head of department"}


def _ship_equipment_options():
    return [
        {"id": equipment.id, "nomenclature": equipment.nomenclature}
        for equipment in ShipEquipment.objects.order_by("nomenclature")
    ]


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------
@extend_schema(tags=["InOut Tag"])
class DashboardView(APIView):
    """GET /dashboard/ -- reproduces `inouthome`'s aggregate KPI/history
    payload (not a page shell): weekly/today counts, pending-approval
    counts, pending-tagin-approvals grouped by department, and a 7-day
    tagout/tagin history series."""

    def get(self, request):
        tagouts = TagOut.objects.filter(active=1)
        tagins = TagIn.objects.filter(active=1)

        profile = getattr(request.user, "user_profile", None)
        if profile is not None:
            if profile.department_id:
                tagouts = tagouts.filter(
                    user_profile__department_id=profile.department_id
                )
            else:
                tagouts = tagouts.filter(created_by=profile)

            is_hod = getattr(
                getattr(profile, "role_master", None), "role_name", None
            ) == (HOD)
            if is_hod and profile.department_id:
                tagins = tagins.filter(
                    Q(tagout__departments_affected=profile.department_id)
                    | Q(created_by=profile)
                ).distinct()
            else:
                tagins = tagins.filter(created_by=profile)
        else:
            tagouts = TagOut.objects.none()
            tagins = TagIn.objects.none()

        today = timezone.localdate()
        start_of_week = today - timedelta(days=6)

        weekly_tagout_count = tagouts.filter(
            date__gte=start_of_week, date__lte=today
        ).count()
        weekly_tagin_count = tagins.filter(
            tagin_date__gte=start_of_week, tagin_date__lte=today
        ).count()
        today_tagout_count = tagouts.filter(date=today).count()
        today_tagin_count = tagins.filter(tagin_date=today).count()

        tagout_pending_approval_count = tagouts.filter(
            approval_status="in_progress"
        ).count()
        tagout_yet_to_tagin_count = (
            tagouts.filter(approval_status="approved").exclude(tagin__active=1).count()
        )

        tagin_pending_qs = TagInApproval.objects.filter(
            active=1, approval_status="pending"
        )
        if profile is not None and getattr(profile, "department", None):
            tagin_pending_qs = tagin_pending_qs.filter(department=profile.department)
        else:
            tagin_pending_qs = TagInApproval.objects.none()

        tagin_pending_by_department = list(
            tagin_pending_qs.values("department__name")
            .annotate(department_name=F("department__name"), count=Count("id"))
            .values("department_name", "count")
            .order_by("department_name")
        )

        history_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            history_data.append(
                {
                    "date": day.strftime("%Y-%m-%d"),
                    "tag_out": tagouts.filter(date=day).count(),
                    "tag_in": tagins.filter(tagin_date=day).count(),
                }
            )

        pending_user_registrations_count = CustomUserProfile.objects.filter(
            is_role=False
        ).count()

        return Response(
            {
                "weekly_tagout_count": weekly_tagout_count,
                "weekly_tagin_count": weekly_tagin_count,
                "today_tagout_count": today_tagout_count,
                "today_tagin_count": today_tagin_count,
                "tagout_pending_approval_count": tagout_pending_approval_count,
                "tagout_yet_to_tagin_count": tagout_yet_to_tagin_count,
                "tagin_pending_by_department": tagin_pending_by_department,
                "history_data": history_data,
                "today_date": today.strftime("%Y-%m-%d"),
                "pending_user_registrations_count": pending_user_registrations_count,
            }
        )


# --------------------------------------------------------------------------
# TagOut
# --------------------------------------------------------------------------


@extend_schema(tags=["InOut Tag"])
class TagOutViewSet(viewsets.ModelViewSet):
    """list() = tagoutlist (default, in-flight only) / history
    (?include_closed=true for the full list, branched inside get_queryset
    instead of a second view). retrieve() = get_tagout_details (legacy ran
    no extra role/department scoping beyond active=1 there, so none is
    added here either). create()/perform_create() = addtagout's POST
    branch. approve = approvetagot. print_slip = print_tagout_slip.
    """

    serializer_class = TagOutSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        qs = (
            TagOut.objects.filter(active=1)
            .select_related(
                "user_profile__ship",
                "user_profile__department",
                "created_by",
                "approved_by",
                "tagout_equipment_name",
            )
            .prefetch_related("departments_affected")
        )

        if self.action != "list":
            # retrieve/approve/print_slip: legacy scoped these purely by
            # active=1 (get_tagout_details) or by an object-level check
            # enforced in the permission class (approve/print_slip) -- not
            # by the department/creator visibility filter below, which is
            # specific to the list screens.
            return qs

        request = self.request
        include_closed = request.query_params.get("include_closed", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if not include_closed:
            # "in-flight" = excludes tagouts that already have an
            # active+approved TagIn (mirrors tagoutlist's .exclude(...)).
            qs = qs.exclude(tagin__active=1, tagin__approval_status="approved")

        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            return qs.none()

        if profile.department_id:
            qs = qs.filter(user_profile__department_id=profile.department_id)
        else:
            qs = qs.filter(created_by=profile)

        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        department = request.query_params.get("department")
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        if department:
            qs = qs.filter(departments_affected__id=department)

        return qs.distinct()

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "user_profile", None)
        if profile is None:
            raise ValidationError(User404)
        department = getattr(profile, "department", None)
        if department is None:
            raise ValidationError(
                "Your account has no department assigned. Contact administrator."
            )

        # Only keep the fields relevant to the chosen tagout_reason -- the
        # rest are dropped rather than silently persisted, matching
        # addtagout's if/elif branching (which never touched the other
        # branches' fields at all).
        reason = serializer.validated_data.get("tagout_reason")
        keep = set(_REASON_ONLY_FIELDS.get(reason, []))
        for field in _ALL_REASON_FIELDS - keep:
            serializer.validated_data.pop(field, None)

        departments_affected = serializer.validated_data.pop("departments_affected", [])
        dept_ids = {d.id for d in departments_affected}
        # Force-include the caller's own department even if not explicitly
        # selected (mirrors addtagout's
        # `if str(user_department_id) not in departments_affected: append`).
        dept_ids.add(department.id)

        with transaction.atomic():
            # Fixes the race condition in TagOut.save()'s tagout_number
            # auto-generation (read-max-then-increment with no locking): the
            # number is derived here under select_for_update() and handed
            # to save() already populated, so the model's own unlocked
            # "if not self.tagout_number" regeneration path never runs.
            year = timezone.now().year
            last_tagout = (
                TagOut.objects.select_for_update()
                .filter(tagout_number__startswith=f"TAG-{year}-")
                .order_by("-tagout_number")
                .first()
            )
            if last_tagout:
                new_serial = int(last_tagout.tagout_number.split("-")[-1]) + 1
            else:
                new_serial = 1
            tagout_number = f"TAG-{year}-{new_serial:03d}"

            tagout = serializer.save(
                user_profile=profile,
                created_by=profile,
                tagout_number=tagout_number,
            )
            tagout.departments_affected.set(Department.objects.filter(id__in=dept_ids))

    @action(detail=False, methods=["get"], url_path="form_meta")
    def form_meta(self, request):
        ship = get_this_ship()
        departments = (
            Department.objects.filter(active=1)
            .exclude(name__in=["ADMIN", "NBCD", "EXECUTIVE", "COMMUNICATION"])
            .order_by("name")
        )

        return Response(
            {
                "ships": [{"id": ship.id, "name": ship.name}] if ship else [],
                "departments": [{"id": d.id, "name": d.name} for d in departments],
                "ship_equipments": _ship_equipment_options(),
                "tagout_reason_choices": [
                    {"value": value, "label": label}
                    for value, label in TagOut.TAG_OUT_REASON_CHOICES
                ],
            }
        )

    @action(detail=False, methods=["get"], url_path="ship_equipments")
    def ship_equipments(self, request):
        return Response({"ship_equipments": _ship_equipment_options()})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        tagout = self.get_object()
        serializer = TagOutApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            raise ValidationError(User404)

        if (
            not _is_hod(profile)
            or profile.department_id != tagout.user_profile.department_id
        ):
            raise PermissionDenied(
                "Only the requesting department's HOD may approve this Tag Out."
            )

        tagout.approval_status = (
            "approved"
            if serializer.validated_data["action"] == "approve"
            else "rejected"
        )
        tagout.approved_by = profile
        tagout.approved_on = timezone.now()
        tagout.save()

        return Response(TagOutSerializer(tagout).data)

    @action(detail=True, methods=["get"], url_path="print_slip")
    def print_slip(self, request, pk=None):
        tagout = self.get_object()

        if tagout.approval_status != "approved":
            raise ValidationError("Only approved tagouts can be printed.")

        if tagout.type == "danger":
            bg_color, border_color, text_color, tag_type = (
                "#ff0000",
                "#8b0000",
                "#000000",
                "DANGER",
            )
        else:
            bg_color, border_color, text_color, tag_type = (
                "#FFDE21",
                "#BA8E23",
                "#000000",
                "WARNING",
            )

        context = {
            "tagout": tagout,
            "tag_type": tag_type,
            "bg_color": bg_color,
            "border_color": border_color,
            "text_color": text_color,
        }
        html_string = render_to_string("tagout_slip_pdf.html", context)
        pdf = HTML(string=html_string).write_pdf()

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="tagout_slip_{tagout.tagout_number}.pdf"'
        )
        return response


# --------------------------------------------------------------------------
# TagIn
# --------------------------------------------------------------------------


@extend_schema(tags=["InOut Tag"])
class TagInViewSet(viewsets.ModelViewSet):
    """list() = tag_in. create()/perform_create() = add_tagin's POST
    branch. form_meta = add_tagin's GET branch. retrieve() =
    get_tagin_details. approve = approvetagin."""

    serializer_class = TagInSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        qs = (
            TagIn.objects.filter(active=1)
            .select_related(
                "tagout__user_profile__ship",
                "tagout__user_profile__department",
                "tagout__tagout_equipment_name",
                "tagout__approved_by",
                "created_by",
            )
            .prefetch_related(
                "tagout__departments_affected",
                "tagin_approvals__department",
                "tagin_approvals__approved_by",
            )
            .order_by("-created_on")
        )

        if self.action != "list":
            return qs

        request = self.request
        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            return qs.none()

        # Stricter than TagOutViewSet's list scoping: only an exact "Head of
        # Department" (not DY HOD) sees the wider department-affected set.
        is_hod = getattr(getattr(profile, "role_master", None), "role_name", None) == (
            HOD
        )
        if is_hod and profile.department_id:
            qs = qs.filter(
                Q(tagout__departments_affected=profile.department_id)
                | Q(created_by=profile)
            ).distinct()
        else:
            qs = qs.filter(created_by=profile)

        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        department = request.query_params.get("department")
        if from_date:
            qs = qs.filter(tagin_date__gte=from_date)
        if to_date:
            qs = qs.filter(tagin_date__lte=to_date)
        if department:
            qs = qs.filter(tagout__user_profile__department__id=department)

        return qs

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "user_profile", None)
        if profile is None:
            raise ValidationError(User404)

        # tagin.ship/.department are dropped here on purpose: TagIn has no
        # such fields, so the legacy add_tagin's
        # `tagin.ship = user_profile.ship` / `tagin.department = ...`
        # assignments were always silent no-ops.
        all_items_returned = serializer.validated_data.get("all_items_returned", True)
        tagin = serializer.save(
            created_by=profile,
            tagin_maintainer_name_rank=serializer.validated_data.get(
                "tagin_maintainer"
            ),
            tagin_remarks=serializer.validated_data.get("tagin_description"),
            # Mirrors add_tagin's `items_pending = items_pending if not
            # all_items_returned else None` -- force-cleared whenever the
            # "all items returned" box is checked, regardless of what the
            # client sent in items_pending.
            items_pending=(
                None
                if all_items_returned
                else serializer.validated_data.get("items_pending")
            ),
        )

        TagInApproval.objects.create(
            tagin=tagin,
            department=tagin.tagout.user_profile.department,
            approval_status="pending",
            created_by=profile,
        )

    @action(detail=False, methods=["get"], url_path="form_meta")
    def form_meta(self, request):
        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            approved_tagouts = TagOut.objects.none()
        else:
            approved_tagouts = (
                TagOut.objects.filter(
                    active=1, approval_status="approved", created_by=profile
                )
                .exclude(
                    id__in=TagIn.objects.filter(active=1).values_list(
                        "tagout_id", flat=True
                    )
                )
                .select_related(
                    "user_profile__ship",
                    "user_profile__department",
                    "created_by",
                    "tagout_equipment_name",
                )
                .order_by("-created_on")
            )
        return Response(TagOutSerializer(approved_tagouts, many=True).data)

    @action(detail=False, methods=["get"], url_path="ship_equipments")
    def ship_equipments(self, request):
        return Response({"ship_equipments": _ship_equipment_options()})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        tagin = self.get_object()
        serializer = TagInApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = getattr(request.user, "user_profile", None)
        if profile is None:
            raise ValidationError(User404)

        if tagin.approval_status == "pending":
            if not _is_co_or_ship_admin(request.user, profile):
                raise PermissionDenied(
                    "Only CO or Ship Admin may provide the first Tag In approval."
                )
            tagin.approval_status = (
                "pending_hod"
                if serializer.validated_data["action"] == "approve"
                else "rejected"
            )
            tagin.status = "in_progress"
            tagin.save(update_fields=["approval_status", "modified_on", "status"])
            return Response(TagInSerializer(tagin).data)

        if tagin.approval_status != "pending_hod":
            raise ValidationError("This Tag In request has already been processed.")

        if _is_hod(profile):
            approval = TagInApproval.objects.filter(
                tagin=tagin,
                department_id=profile.department_id,
                active=1,
                approval_status="pending",
            ).first()
        else:
            raise PermissionDenied(
                "Only the affected department HOD may provide the final Tag In approval."
            )
        if approval is None:
            raise NotFound(
                "You do not have a pending approval for this Tag In request."
            )

        action_value = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")

        approval.approval_status = (
            "approved" if action_value == "approve" else "rejected"
        )
        approval.approved_by = profile
        approval.approved_on = timezone.now()
        if remarks:
            approval.remarks = remarks
        approval.save()

        tagin.check_all_approvals()

        return Response(TagInSerializer(tagin).data)


@extend_schema(tags=["InOut Tag"])
class HistoryAPIView(APIView):
    def get(self, request):
        user_profile = getattr(request.user, "user_profile", None)

        if not user_profile:
            return Response(
                {
                    "status": "success",
                    "data": [],
                    "departments": [],
                },
                status=status.HTTP_200_OK,
            )

        tagouts = (
            TagOut.objects.filter(active=1)
            .select_related(
                "user_profile__ship",
                "user_profile__department",
                "created_by",
                "approved_by",
                "tagin",
            )
            .prefetch_related(
                "departments_affected",
            )
        )

        # DY HOD / HOD -> records from their department
        role_master = user_profile.role_master
        is_dyhod = bool(role_master and role_master.role_name in {"DY HOD", HOD})

        if is_dyhod and user_profile.department:
            tagouts = tagouts.filter(user_profile__department=user_profile.department)
        else:
            # Other users -> only their own records
            tagouts = tagouts.filter(created_by=user_profile)

        # Filters
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        department = request.query_params.get("department")

        if from_date:
            tagouts = tagouts.filter(date__gte=from_date)

        if to_date:
            tagouts = tagouts.filter(date__lte=to_date)

        if department:
            tagouts = tagouts.filter(departments_affected__id=department)

        tagouts = tagouts.distinct().order_by("-date", "-id")

        departments = Department.objects.filter(active=1).order_by("name")

        return Response(
            {
                "status": "success",
                "data": HistorySerializer(
                    tagouts,
                    many=True,
                ).data,
                "departments": [
                    {
                        "id": dept.id,
                        "name": dept.name,
                    }
                    for dept in departments
                ],
                "filters": {
                    "from_date": from_date or "",
                    "to_date": to_date or "",
                    "department": department or "",
                },
                "is_dyhod": is_dyhod,
            },
            status=status.HTTP_200_OK,
        )
