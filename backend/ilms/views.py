from django.db import transaction
from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import models, serializers
from .excel import ExcelImportExportMixin
from .utils import tagged_viewset


def _normalize_ids(value):
    if value in (None, ""):
        return []
    if isinstance(value, (str, int)):
        return [value]
    return list(value)


def _extract_sync_ids(request):
    ids = _normalize_ids(request.data.get("ids") or request.data.get("pks"))
    items = request.data.get("items") or []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ids.append(item["id"])
    return ids


def _sync_workflow_rows(
    request,
    model,
    serializer_class,
    completion_field,
    status_field,
    ids,
):
    queryset = model.objects.filter(is_sync=False)
    department_id = _request_user_department_id(request)
    if department_id:
        queryset = queryset.filter(custom_user__department_id=department_id)
    if ids:
        queryset = queryset.filter(pk__in=ids)
    else:
        queryset = queryset.filter(is_hod_approval=True)

    with transaction.atomic():
        rows = list(queryset.select_for_update())
        for row in rows:
            setattr(row, completion_field, True)
            row.is_sync = True
            row.in_progress_status = "Synced"
            setattr(row, status_field, "Synced")

        if rows:
            model.objects.bulk_update(
                rows,
                [completion_field, "is_sync", "in_progress_status", status_field],
            )

    return Response(
        {
            "status": "success" if rows else "warning",
            "message": (
                "Data processed successfully"
                if rows
                else "No approved unsynced records found"
            ),
            "updated": len(rows),
            "count": len(rows),
            "data": serializer_class(rows, many=True).data,
        }
    )


@extend_schema(
    summary="Demand data sync to ILMS",
    tags=["ILMS"],
)
@api_view(["POST"])
def demand_data_send_ilms(request):
    return _sync_workflow_rows(
        request,
        models.DemandDetails,
        serializers.DemandDetailsSerializer,
        "is_demand",
        "mo_status",
        _extract_sync_ids(request),
    )


@extend_schema(
    summary="PTS data sync to ILMS",
    tags=["ILMS"],
)
@api_view(["POST"])
def pts_data_send_ilms(request):
    return _sync_workflow_rows(
        request,
        models.PTSDetails,
        serializers.PTSDetailsSerializer,
        "is_pts",
        "mo_pts_status",
        _extract_sync_ids(request),
    )


def _request_user_profile(request):
    profile = getattr(request.user, "user_profile", None)
    if profile is None:
        raise ValidationError(
            {"user_profile": "Authenticated user has no linked user profile."}
        )
    return profile


def _request_user_department_id(request):
    profile = getattr(request.user, "user_profile", None)
    department_id = getattr(profile, "department_id", None)
    if department_id is None:
        department_id = getattr(request.user, "department_id", None)
    return department_id


@api_view(["POST"])
def approve_pts(request):
    pk = request.data.get("pts_id") or request.data.get("id") or request.data.get("pk")
    cart_type = request.data.get("cart_name") or request.data.get("cart_type") or "PTS"

    if not pk:
        raise ValidationError({"pts_id": "PTS ID is required."})

    model_map = {
        "PTS": models.PTSDetails,
        "Demand": models.DemandDetails,
        "Survey": models.SurveyDetails,
    }
    model = model_map.get(str(cart_type).strip())
    if model is None:
        raise ValidationError({"cart_name": f"Invalid cart type: {cart_type}"})

    obj = model.objects.filter(pk=pk).first()
    if obj is None:
        raise ValidationError({"pts_id": "Record not found."})

    if obj.is_hod_approval:
        return Response({"status": "warning", "message": "Already approved"})

    obj.is_hod_approval = True
    obj.in_progress_status = "Approved"
    update_fields = ["is_hod_approval", "in_progress_status"]
    status_field = {
        models.PTSDetails: "mo_pts_status",
        models.DemandDetails: "mo_status",
        models.SurveyDetails: "mo_survey_status",
    }[model]
    setattr(obj, status_field, "Approved")
    update_fields.append(status_field)
    obj.save(update_fields=update_fields)

    return Response(
        {
            "status": "success",
            "message": f"{cart_type} approved successfully",
        }
    )


@extend_schema(
    summary="Combined ILMS inbox",
    description=(
        "Merges HOD-submitted PTS, Demand and Survey entries into a single "
        "annotated list, matching the reference ILMS Action/inbox view."
    ),
    tags=["ILMS"],
)
@api_view(["GET"])
def ilms_combined_inbox(request):
    allowed_equipment_class_ids = _scoped_equipment_class_ids(request)

    def scoped(queryset):
        return queryset.filter(
            Q(mo_routine_plan__isnull=False)
            | Q(mo_dart__isnull=False)
            | Q(obs_spare_id__equipment_class_id__in=allowed_equipment_class_ids)
        )

    pts_qs = scoped(
        models.PTSDetails.objects.filter(is_hod=True).select_related(
            "ilms_spare_id",
            "vendor_id",
            "obs_spare_id",
            "mo_routine_plan__item_id",
            "mo_dart__dart_id__equipment_ems",
        )
    ).order_by("-id")
    demand_qs = scoped(
        models.DemandDetails.objects.filter(is_hod=True).select_related(
            "ilms_spare_id",
            "vendor_id",
            "obs_spare_id",
            "mo_routine_plan__item_id",
            "mo_dart__dart_id__equipment_ems",
        )
    ).order_by("-id")
    survey_qs = scoped(
        models.SurveyDetails.objects.filter(is_hod=True).select_related(
            "ilms_spare_id",
            "obs_spare_id",
            "mo_routine_plan__item_id",
            "mo_dart__dart_id__equipment_ems",
        )
    ).order_by("-id")

    department_id = request.user.department_id
    if department_id:
        pts_qs = pts_qs.filter(custom_user__department_id=department_id)
        demand_qs = demand_qs.filter(custom_user__department_id=department_id)
        survey_qs = survey_qs.filter(custom_user__department_id=department_id)

    pts_entries = [_annotate_pending_ilms_entry(entry) for entry in pts_qs]
    demand_entries = [_annotate_pending_ilms_entry(entry) for entry in demand_qs]
    survey_entries = [_annotate_pending_ilms_entry(entry) for entry in survey_qs]

    def serialize(entry, serializer_class):
        data = serializer_class(entry).data
        for field in (
            "dart_number",
            "equipment_name",
            "equipment_nomenclature",
            "dart_description",
            "quantity_required",
            "equipment_class",
        ):
            data[field] = getattr(entry, field, "—")
        return data

    all_entries = (
        [serialize(entry, serializers.PTSDetailsSerializer) for entry in pts_entries]
        + [
            serialize(entry, serializers.DemandDetailsSerializer)
            for entry in demand_entries
        ]
        + [
            serialize(entry, serializers.SurveyDetailsSerializer)
            for entry in survey_entries
        ]
    )
    return Response({"pts_entries": all_entries})


def _scoped_equipment_class_ids(request):
    from obs.models import EquipmentClass

    department_id = _request_user_department_id(request)
    if not department_id:
        return EquipmentClass.objects.none().values_list("id", flat=True)

    return EquipmentClass.objects.filter(
        spare_class__department_id=department_id
    ).values_list("id", flat=True)


def _routine_description_summary(routine_description_id):
    if not routine_description_id:
        return None

    from ems.models import RoutineDescription

    return (
        RoutineDescription.objects.filter(pk=routine_description_id)
        .values(
            "dart_number",
            "routine_description",
            "equipment_name__name",
            "equipment_name__extra",
            "equipment_name__sfd_equipment_id",
        )
        .first()
    )


def _annotate_pending_ilms_entry(entry):
    """Attach dart_number/equipment_name/equipment_class/quantity_required
    display fields, matching the reference mo_survey/demand/pts list views.
    """
    entry.dart_number = "—"
    entry.equipment_name = "—"
    entry.equipment_nomenclature = "—"
    entry.dart_description = "—"
    entry.quantity_required = "—"
    entry.equipment_class = "—"

    try:
        if entry.mo_routine_plan_id:
            planned_desc = entry.mo_routine_plan
            rd = _routine_description_summary(planned_desc.routine_description_id_id)
            if rd:
                entry.dart_number = rd.get("dart_number") or "—"
                entry.dart_description = rd.get("routine_description") or "—"
                entry.equipment_nomenclature = rd.get("equipment_name__name") or "—"
                entry.equipment_name = rd.get("equipment_name__extra") or "—"
                sfd_eq_id = rd.get("equipment_name__sfd_equipment_id")
                if sfd_eq_id and planned_desc.item_id:
                    mo_map = (
                        models.MoMappingTable.objects.filter(
                            ilms_spare_id=planned_desc.item_id,
                            equipment_id=sfd_eq_id,
                        )
                        .select_related("equipment__equipment")
                        .first()
                    )
                    if mo_map and mo_map.equipment and mo_map.equipment.equipment:
                        entry.equipment_class = (
                            mo_map.equipment.equipment.equipment_class or "—"
                        )
            planned_spare = models.PlannedMOSpareList.objects.filter(
                planned_spares_description=planned_desc
            ).first()
            entry.quantity_required = (
                planned_spare.quantity_required if planned_spare else "—"
            )
            return entry

        if entry.mo_dart_id:
            dart_mo = entry.mo_dart
            if dart_mo.dart_id:
                entry.dart_number = dart_mo.dart_id.dart_number or "—"
                entry.dart_description = dart_mo.dart_id.defective_discriptions or "—"
                if dart_mo.dart_id.equipment_ems:
                    entry.equipment_nomenclature = (
                        dart_mo.dart_id.equipment_ems.name or "—"
                    )
                    entry.equipment_name = dart_mo.dart_id.equipment_ems.extra or "—"
            entry.quantity_required = dart_mo.quantity or "—"
            if dart_mo.equipment_id_id and entry.ilms_spare_id_id:
                mo_map = (
                    models.MoMappingTable.objects.filter(
                        ilms_spare_id=entry.ilms_spare_id,
                        equipment=dart_mo.equipment_id,
                    )
                    .select_related("equipment__equipment")
                    .first()
                )
                if mo_map and mo_map.equipment and mo_map.equipment.equipment:
                    entry.equipment_class = (
                        mo_map.equipment.equipment.equipment_class or "—"
                    )
            return entry

        if entry.obs_spare_id_id:
            from dart.models import DartSpare
            from obs.models import Demand as ObsDemand
            from obs.models import Survey as ObsSurvey

            dart_spare = (
                DartSpare.objects.filter(spare_id=entry.obs_spare_id_id)
                .select_related("dart")
                .order_by("-dart_id")
                .first()
            )
            if dart_spare and dart_spare.dart:
                entry.dart_number = dart_spare.dart.dart_number or "—"
                entry.dart_description = dart_spare.dart.defective_discriptions or "—"
                if dart_spare.dart.equipment_ems:
                    entry.equipment_nomenclature = (
                        dart_spare.dart.equipment_ems.name or "—"
                    )
                    entry.equipment_name = dart_spare.dart.equipment_ems.extra or "—"

            if entry.obs_spare_id.equipment_class:
                entry.equipment_class = entry.obs_spare_id.equipment_class.name or "—"

            survey_qty = (
                ObsSurvey.objects.filter(spare=entry.obs_spare_id)
                .order_by("-id")
                .first()
            )
            if survey_qty:
                entry.quantity_required = survey_qty.quantity_tosurvey
            else:
                demand_qty = (
                    ObsDemand.objects.filter(spare=entry.obs_spare_id)
                    .order_by("-id")
                    .first()
                )
                entry.quantity_required = (
                    demand_qty.quantity_todemand if demand_qty else "—"
                )
    except Exception:
        entry.dart_number = "—"
        entry.equipment_name = "—"
        entry.equipment_nomenclature = "—"
        entry.dart_description = "—"
        entry.quantity_required = "—"
        entry.equipment_class = "—"

    return entry


@extend_schema(tags=["ILMS"])
class ILMSModelViewSet(ExcelImportExportMixin, viewsets.ModelViewSet):
    pass


class ApprovalWorkflowMixin:
    workflow_name = ""
    completion_field = ""
    status_field = ""

    @action(detail=False, methods=["get"], url_path="pending-list")
    def pending_list(self, request):
        queryset = (
            self.get_queryset()
            .select_related(
                "ilms_spare_id",
                "obs_spare_id",
                "mo_dart__dart_id__equipment_ems",
                "mo_dart__equipment_id__equipment",
                "obs_spare_id__equipment_class",
                "mo_routine_plan__item_id",
            )
            .order_by("-id")
        )
        allowed_equipment_class_ids = _scoped_equipment_class_ids(request)
        queryset = queryset.filter(
            Q(mo_routine_plan__isnull=False)
            | Q(mo_dart__isnull=False)
            | Q(obs_spare_id__equipment_class_id__in=allowed_equipment_class_ids)
        )
        department_id = _request_user_department_id(request)
        if department_id:
            queryset = queryset.filter(custom_user__department_id=department_id)

        entries = [_annotate_pending_ilms_entry(entry) for entry in queryset]

        data = []
        for entry in entries:
            row = self.get_serializer(entry).data
            for field in (
                "dart_number",
                "equipment_name",
                "equipment_nomenclature",
                "dart_description",
                "quantity_required",
                "equipment_class",
            ):
                row[field] = getattr(entry, field, "—")
            data.append(row)
        return Response(data)

    @action(detail=True, methods=["post"], url_path="send-for-approval")
    def send_for_approval(self, request, pk=None):
        entry = self.get_object()
        if entry.is_hod_approval:
            raise ValidationError(
                {"detail": "Approved records cannot be submitted again."}
            )
        entry.is_hod = True
        entry.in_progress_status = self.workflow_name
        update_fields = ["is_hod", "in_progress_status"]
        if self.status_field:
            setattr(entry, self.status_field, "Pending HOD Approval")
            update_fields.append(self.status_field)
        entry.save(update_fields=update_fields)
        return Response(self.get_serializer(entry).data)

    @action(detail=False, methods=["post"], url_path="bulk-send-for-approval")
    def bulk_send_for_approval(self, request):
        ids = request.data.get("ids", request.data.get("pks", []))
        if not ids:
            raise ValidationError({"ids": "At least one record id is required."})
        update_kwargs = {
            "is_hod": True,
            "in_progress_status": self.workflow_name,
        }
        if self.status_field:
            update_kwargs[self.status_field] = "Pending HOD Approval"
        updated = (
            self.get_queryset()
            .filter(
                pk__in=ids,
                is_hod_approval=False,
            )
            .update(**update_kwargs)
        )
        return Response({"success": True, "updated": updated})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_hod:
            raise ValidationError(
                {"detail": "Record must be submitted to HOD before approval."}
            )
        entry.is_hod_approval = True
        entry.in_progress_status = "Approved"
        update_fields = ["is_hod_approval", "in_progress_status"]
        if self.status_field:
            setattr(entry, self.status_field, "Approved")
            update_fields.append(self.status_field)
        entry.save(update_fields=update_fields)
        return Response(self.get_serializer(entry).data)

    @action(detail=False, methods=["post"], url_path="bulk-approve")
    def bulk_approve(self, request):
        ids = request.data.get("ids", request.data.get("pks", []))
        if not ids:
            raise ValidationError({"ids": "At least one record id is required."})
        update_kwargs = {
            "is_hod_approval": True,
            "in_progress_status": "Approved",
        }
        if self.status_field:
            update_kwargs[self.status_field] = "Approved"
        updated = (
            self.get_queryset()
            .filter(
                pk__in=ids,
                is_hod=True,
                is_hod_approval=False,
            )
            .update(**update_kwargs)
        )
        return Response({"success": True, "updated": updated})

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        queryset = self.get_queryset().filter(
            is_hod=True,
            is_hod_approval=False,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def outbox(self, request):
        queryset = self.get_queryset().filter(
            is_hod=True,
            is_hod_approval=True,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_hod_approval:
            raise ValidationError(
                {"detail": "HOD approval is required before completion."}
            )
        setattr(entry, self.completion_field, True)
        entry.in_progress_status = "Completed"
        update_fields = [self.completion_field, "in_progress_status"]
        if self.status_field:
            setattr(entry, self.status_field, "Completed")
            update_fields.append(self.status_field)
        entry.save(update_fields=update_fields)
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"], url_path="mark-synced")
    def mark_synced(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_hod_approval:
            raise ValidationError(
                {"detail": "HOD approval is required before marking it synced."}
            )
        setattr(entry, self.completion_field, True)
        entry.is_sync = True
        entry.in_progress_status = "Synced"
        update_fields = [self.completion_field, "is_sync", "in_progress_status"]
        if self.status_field:
            setattr(entry, self.status_field, "Synced")
            update_fields.append(self.status_field)
        entry.save(update_fields=update_fields)
        return Response(self.get_serializer(entry).data)

    def _resolve_cart_items(self, source, source_ids):
        if source == "planned":
            entries = models.PlannedMOSpareList.objects.filter(
                pk__in=source_ids,
                is_deleted=False,
            ).select_related("planned_spares_description__item_id")
            return [
                {
                    "ilms_spare_id": entry.planned_spares_description.item_id,
                    "obs_spare_id": None,
                    "mo_routine_plan": entry.planned_spares_description,
                    "mo_dart": None,
                }
                for entry in entries
                if entry.planned_spares_description.item_id
            ]
        if source == "dart":
            entries = models.DartMOSpare.objects.filter(
                pk__in=source_ids,
                is_delete=False,
            ).select_related("mo_spare")
            return [
                {
                    "ilms_spare_id": entry.mo_spare,
                    "obs_spare_id": None,
                    "mo_routine_plan": None,
                    "mo_dart": entry,
                }
                for entry in entries
                if entry.mo_spare
            ]

        from obs.models import Spares

        return [
            {
                "ilms_spare_id": None,
                "obs_spare_id": spare,
                "mo_routine_plan": None,
                "mo_dart": None,
            }
            for spare in Spares.objects.filter(pk__in=source_ids)
        ]

    @extend_schema(request=serializers.AddToWorkflowCartSerializer)
    @action(detail=False, methods=["post"], url_path="add-to-cart")
    def add_to_cart(self, request):
        serializer = serializers.AddToWorkflowCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data["source"]
        source_ids = serializer.validated_data["source_ids"]
        resolved_items = self._resolve_cart_items(source, source_ids)
        if len(resolved_items) != len(set(source_ids)):
            raise ValidationError(
                {"source_ids": "One or more source records were not found."}
            )

        created_entries = []
        with transaction.atomic():
            for item in resolved_items:
                lookup = {
                    "ilms_spare_id": item["ilms_spare_id"],
                    "obs_spare_id": item["obs_spare_id"],
                    "mo_routine_plan": item["mo_routine_plan"],
                    "mo_dart": item["mo_dart"],
                }
                entry, _ = self.get_queryset().get_or_create(
                    **lookup,
                    defaults={
                        "custom_user": _request_user_profile(request),
                        "in_progress_status": "Pending",
                    },
                )
                created_entries.append(entry)

        return Response(
            self.get_serializer(created_entries, many=True).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["ILMS"])
class WedInventoryViewSet(viewsets.ViewSet):
    """Read-only WED-inventory views over `obs` models, matching the
    reference ILMS wed_item_search/wed_survey_list/etc. views (these are a
    distinct, obs-backed inventory view separate from the ILMS/MO models).
    """

    @action(detail=False, methods=["get"], url_path="item-search")
    def item_search(self, request):
        from obs.models import Spares
        from obs.serializers import SparesSerializer

        item_code = request.query_params.get("item_code", "").strip()
        item_description = request.query_params.get("item_description", "").strip()
        vendor_code = request.query_params.get("vendor_code", "").strip()

        spares = Spares.objects.filter(
            Q(authority__name="WED ITEM") | Q(authority__name="B & D")
        )
        if item_code:
            spares = spares.filter(pattern_number__icontains=item_code)
        if item_description:
            spares = spares.filter(description__icontains=item_description)
        if vendor_code:
            spares = spares.filter(pattern_number__startswith=vendor_code)

        return Response(SparesSerializer(spares, many=True).data)

    @action(detail=False, methods=["get"], url_path="survey-list")
    def survey_list(self, request):
        from obs.models import EquipmentClass, Survey
        from obs.serializers import SurveySerializer

        equipment_class_ids = EquipmentClass.objects.filter(
            spare_class__department_id=request.user.department_id
        ).values_list("id", flat=True)
        entries = list(
            Survey.objects.filter(spare__equipment_class_id__in=equipment_class_ids)
        )
        for entry in entries:
            if not entry.dart_number:
                entry.dart_number = "Pending"
        return Response(SurveySerializer(entries, many=True).data)

    @action(detail=False, methods=["get"], url_path="demand-list")
    def demand_list(self, request):
        from obs.models import Demand, EquipmentClass
        from obs.serializers import DemandSerializer

        equipment_class_ids = EquipmentClass.objects.filter(
            spare_class__department_id=request.user.department_id
        ).values_list("id", flat=True)
        entries = list(
            Demand.objects.filter(spare__equipment_class_id__in=equipment_class_ids)
        )
        for entry in entries:
            if not entry.dart_number:
                entry.dart_number = "Pending"
        return Response(DemandSerializer(entries, many=True).data)

    @action(detail=False, methods=["get"], url_path="receive-list")
    def receive_list(self, request):
        from obs.models import Receive
        from obs.serializers import ReceiveSerializer

        entries = Receive.objects.filter(
            spare__equipment_class__spare_class__department_id=(
                request.user.department_id
            )
        )
        return Response(ReceiveSerializer(entries, many=True).data)

    @action(detail=False, methods=["get"], url_path="pts-list")
    def pts_list(self, request):
        from obs.models import PostSurvey
        from obs.serializers import PostSurveySerializer

        entries = PostSurvey.objects.filter(
            survey_number__in=["PTS", "OPDEM", "ONETIME APPROVAL"],
            spare__equipment_class__spare_class__department_id=(
                request.user.department_id
            ),
            has_pts=True,
        )
        return Response(PostSurveySerializer(entries, many=True).data)

    @action(detail=False, methods=["get"], url_path="generate-demand-list")
    def generate_demand_list(self, request):
        from obs.models import Demand, EquipmentClass, PostDemand, Spares
        from obs.serializers import DemandSerializer

        equipment_class_ids = EquipmentClass.objects.filter(
            spare_class__department_id=request.user.department_id
        ).values_list("id", flat=True)
        spare_ids = Spares.objects.filter(
            equipment_class_id__in=equipment_class_ids
        ).values_list("id", flat=True)
        post_demand_spare_ids = PostDemand.objects.filter(
            spare_id__in=spare_ids
        ).values_list("spare_id", flat=True)
        entries = Demand.objects.filter(spare_id__in=spare_ids).exclude(
            spare_id__in=post_demand_spare_ids
        )
        return Response(DemandSerializer(entries, many=True).data)

    @action(detail=False, methods=["post"], url_path="save-demand")
    def save_demand(self, request):
        from django.utils import timezone

        from obs.models import Demand, PostDemand

        demand_id = request.data.get("id")
        quantity = request.data.get("quantity")
        demand_obj = Demand.objects.filter(id=demand_id).first()
        if not demand_obj:
            raise ValidationError({"id": "Demand not found."})

        post_demand = PostDemand.objects.create(
            spare=demand_obj.spare,
            quantity_demanded=quantity,
            demand_number="",
            demand_date=timezone.now(),
        )
        demand_number = f"DEMAND_{str(post_demand.id).zfill(4)}"
        post_demand.demand_number = demand_number
        post_demand.save(update_fields=["demand_number"])
        return Response({"status": "success", "demand_number": demand_number})

    @action(detail=False, methods=["get"], url_path="demanded-spares")
    def demanded_spares(self, request):
        from obs.models import PostDemand
        from obs.serializers import PostDemandSerializer

        entries = PostDemand.objects.all().order_by("-id")
        return Response(PostDemandSerializer(entries, many=True).data)


@tagged_viewset("ILMS")
class MOItemEquipmentViewSet(ILMSModelViewSet):
    queryset = models.MOItemEquipment.objects.all()
    serializer_class = serializers.MOItemEquipmentSerializer


@tagged_viewset(
    "ILMS",
    create_examples=[
        OpenApiExample(
            "Create item",
            value={
                "item_code": "ILMS-1001",
                "section_head": "ENGINEERING",
                "item_desc": "HYDRAULIC FILTER ELEMENT",
                "country_code": "IN",
                "item_deno": "NOS",
                "months_shelf_life": 24,
                "crp_category": "C",
                "ved_category": "V",
                "abc_category": "A",
                "review_sub_section_code": "ENG",
                "incat_yn": True,
            },
            request_only=True,
        )
    ],
)
class ItemViewSet(ILMSModelViewSet):
    queryset = models.Item.objects.all()
    serializer_class = serializers.ItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(
                Q(item_code__icontains=query) | Q(item_desc__icontains=query)
            )
        section_head = self.request.query_params.get("section_head")
        category = self.request.query_params.get("category")
        incatted = self.request.query_params.get("incatted")
        if section_head:
            queryset = queryset.filter(section_head__iexact=section_head)
        if category:
            queryset = queryset.filter(crp_category__iexact=category)
        if incatted is not None:
            queryset = queryset.filter(
                incat_yn=incatted.lower() in {"1", "true", "yes"}
            )
        return queryset

    def _scoped_item_ids(self, request):
        return models.MoMappingTable.objects.filter(
            equipment__department_id=request.user.department_id
        ).values_list("ilms_spare_id", flat=True)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        item_ids = self._scoped_item_ids(request)
        hod_inbox = (
            models.SurveyDetails.objects.filter(
                is_hod=True, ilms_spare_id__in=item_ids
            ).count()
            + models.PTSDetails.objects.filter(
                is_hod=True, ilms_spare_id__in=item_ids
            ).count()
            + models.DemandDetails.objects.filter(
                is_hod=True, ilms_spare_id__in=item_ids
            ).count()
        )
        approved_actions = (
            models.SurveyDetails.objects.filter(
                is_hod_approval=True, ilms_spare_id__in=item_ids
            ).count()
            + models.PTSDetails.objects.filter(
                is_hod_approval=True, ilms_spare_id__in=item_ids
            ).count()
            + models.DemandDetails.objects.filter(
                is_hod_approval=True, ilms_spare_id__in=item_ids
            ).count()
        )
        return Response(
            {
                "items": self.get_queryset().filter(pk__in=item_ids).count(),
                "vendors": models.Vendor.objects.count(),
                "mapped_items": models.MoMappingTable.objects.filter(
                    ilms_spare_id__in=item_ids
                ).count(),
                "pending_surveys": models.SurveyDetails.objects.filter(
                    is_survey=False, ilms_spare_id__in=item_ids
                ).count(),
                "pending_pts": models.PTSDetails.objects.filter(
                    is_pts=False, ilms_spare_id__in=item_ids
                ).count(),
                "pending_demands": models.DemandDetails.objects.filter(
                    is_demand=False, ilms_spare_id__in=item_ids
                ).count(),
                "hod_inbox": hod_inbox,
                "approved_actions": approved_actions,
                "pending_iif": models.IIF.objects.filter(
                    is_delete=False,
                    is_sync=False,
                ).count(),
            }
        )

    @action(detail=True, methods=["get"])
    def context(self, request, pk=None):
        item = self.get_object()
        mappings = models.MoMappingTable.objects.filter(
            ilms_spare_id=item
        ).select_related("vendor_id", "equipment")
        surveys = models.SurveyDetails.objects.filter(ilms_spare_id=item)
        pts_entries = models.PTSDetails.objects.filter(ilms_spare_id=item)
        demands = models.DemandDetails.objects.filter(ilms_spare_id=item)
        issued_items = models.ItemIssued.objects.filter(item=item).select_related(
            "customer"
        )

        return Response(
            {
                "item": self.get_serializer(item).data,
                "mappings": serializers.MoMappingTableSerializer(
                    mappings,
                    many=True,
                ).data,
                "surveys": serializers.SurveyDetailsSerializer(
                    surveys,
                    many=True,
                ).data,
                "pts": serializers.PTSDetailsSerializer(
                    pts_entries,
                    many=True,
                ).data,
                "demands": serializers.DemandDetailsSerializer(
                    demands,
                    many=True,
                ).data,
                "issued_items": serializers.ItemIssuedSerializer(
                    issued_items,
                    many=True,
                ).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="search-list")
    def search_list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @action(detail=False, methods=["get"], url_path="search-enriched")
    def search_enriched(self, request):
        item_objects = self.get_queryset()[:100]
        item_code_list = list(item_objects.values_list("item_code", flat=True))

        stations_map = {}
        item_lines = models.ItemLine.objects.filter(
            item_code__in=item_code_list
        ).values(
            "item_code_id", "station_code", "sh_no", "datetime_added", "datetime_closed"
        )
        for line in item_lines:
            stations_map.setdefault(str(line["item_code_id"]), []).append(
                {
                    "station_code": line["station_code"],
                    "sh_no": line["sh_no"],
                    "available": "NO" if line["datetime_closed"] else "YES",
                    "datetime_added": (
                        str(line["datetime_added"]) if line["datetime_added"] else None
                    ),
                }
            )

        mo_mappings = (
            models.MoMappingTable.objects.filter(
                ilms_spare_id__item_code__in=item_code_list,
                equipment__isnull=False,
            )
            .select_related("ilms_spare_id", "equipment", "equipment__equipment")
            .values(
                "ilms_spare_id__item_code",
                "equipment__id",
                "equipment__equipment__equipment_code",
                "equipment__nomenclature",
            )
        )
        equipment_map = {}
        for mapping in mo_mappings:
            item_code = mapping["ilms_spare_id__item_code"]
            equipment_map.setdefault(
                item_code,
                {
                    "equipment_code": (
                        mapping["equipment__equipment__equipment_code"] or ""
                    ),
                    "equipment_id": (
                        str(mapping["equipment__id"])
                        if mapping["equipment__id"]
                        else ""
                    ),
                    "nomenclature": mapping["equipment__nomenclature"] or "",
                },
            )

        item_details = []
        for item in item_objects:
            key = str(item.item_code)
            eq_info = equipment_map.get(key, {})
            item_details.append(
                {
                    "item_code": item.item_code,
                    "section_head": item.section_head,
                    "item_desc": item.item_desc,
                    "country_code": item.country_code,
                    "item_deno": item.item_deno,
                    "months_shelf_life": item.months_shelf_life,
                    "crp_category": item.crp_category,
                    "ved_category": item.ved_category,
                    "abc_category": item.abc_category,
                    "datetime_approved": (
                        str(item.datetime_approved) if item.datetime_approved else None
                    ),
                    "approved_by": item.approved_by,
                    "incat_yn": item.incat_yn,
                    "stations": stations_map.get(key, []),
                    "equipment_code": eq_info.get("equipment_code", ""),
                    "equipment_id": eq_info.get("equipment_id", ""),
                    "nomenclature": eq_info.get("nomenclature", ""),
                }
            )

        from ems.models import RoutineDescription

        routine_list = (
            RoutineDescription.objects.filter(
                department_f_key_id=request.user.department_id
            )
            .order_by("-id")
            .values("id", "dart_number", "routine_description")
        )

        return Response(
            {
                "items": item_details,
                "routine_list": list(routine_list),
            }
        )


@tagged_viewset(
    "ILMS",
    create_examples=[
        OpenApiExample(
            "Create vendor",
            value={
                "vendor_code": "VEN-001",
                "name": "NAVAL SPARES SUPPLIER",
                "vendor_class": "OEM",
                "country_code": "IN",
            },
            request_only=True,
        )
    ],
)
class VendorViewSet(ILMSModelViewSet):
    queryset = models.Vendor.objects.all()
    serializer_class = serializers.VendorSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset

    @action(detail=False, methods=["get"], url_path="search-list")
    def search_list(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @action(detail=False, methods=["get"], url_path="search-table")
    def search_table(self, request):
        vendor_code = request.query_params.get("vendor_code", "").strip()
        vendor_name = request.query_params.get("vendor_name", "").strip()
        vendors = models.Vendor.objects.all()
        if vendor_code:
            vendors = vendors.filter(vendor_code__icontains=vendor_code)
        if vendor_name:
            vendors = vendors.filter(name__icontains=vendor_name)
        vendors = vendors[:100]

        data = [
            {
                "ser": index,
                "vendor_code": vendor.vendor_code or "-",
                "vendor_name": vendor.name or "-",
                "vendor_class": vendor.vendor_class or "-",
                "addressee": vendor.addressee or "-",
                "approved_by": vendor.approved_by or "-",
                "date_approved": (
                    vendor.datetime_approved.strftime("%Y-%m-%d")
                    if vendor.datetime_approved
                    else "-"
                ),
                "date_banupto": (
                    str(vendor.date_banned_upto) if vendor.date_banned_upto else "-"
                ),
                "city": vendor.city or "-",
                "state": vendor.state or "-",
                "add_line1": vendor.address_line1 or "-",
                "add_line2": vendor.address_line2 or "-",
                "add_line3": vendor.address_line3 or "-",
                "pincode": vendor.pin_code or "-",
                "country_cd": vendor.country_code or "-",
                "remarks": vendor.remarks or "-",
                "gst_no": vendor.gst_no or "-",
            }
            for index, vendor in enumerate(vendors, start=1)
        ]
        return Response({"status": "success", "data": data})


@tagged_viewset("ILMS")
class MoMappingTableViewSet(ILMSModelViewSet):
    queryset = models.MoMappingTable.objects.select_related(
        "equipment",
        "ilms_spare_id",
        "vendor_id",
    )
    serializer_class = serializers.MoMappingTableSerializer


@tagged_viewset("ILMS")
class MOPlannedSparesDescriptionViewSet(ILMSModelViewSet):
    queryset = models.MOPlannedSparesDescription.objects.select_related(
        "item_id",
        "routine_description_id",
    )
    serializer_class = serializers.MOPlannedSparesDescriptionSerializer


@tagged_viewset("ILMS")
class PlannedMOSpareListViewSet(ILMSModelViewSet):
    queryset = models.PlannedMOSpareList.objects.select_related(
        "planned_spares_description",
    )
    serializer_class = serializers.PlannedMOSpareListSerializer

    @action(detail=False, methods=["get"], url_path="by-routine")
    def by_routine(self, request):
        routine_description = request.query_params.get("routine_description")
        if not routine_description:
            raise ValidationError(
                {"routine_description": "This query parameter is required."}
            )
        queryset = self.get_queryset().filter(
            planned_spares_description__routine_description_id=(routine_description),
            is_deleted=False,
            planned_spares_description__is_deleted=False,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="routines-by-department",
    )
    def routines_by_department(self, request):
        from ems.models import RoutineDescription

        routines = (
            RoutineDescription.objects.exclude(dart_number__isnull=True)
            .exclude(dart_number="")
            .filter(department_f_key_id=request.user.department_id)
            .values(
                "id",
                "dart_number",
                "routine_description",
                "maintop_no",
                "equipment_name__name",
                "equipment_name__nomenclature",
                "equipment_name__extra",
            )
        )
        return Response({"success": True, "routines": list(routines)})


@tagged_viewset("ILMS")
class SurveyDetailsViewSet(ApprovalWorkflowMixin, ILMSModelViewSet):
    workflow_name = "Survey"
    completion_field = "is_survey"
    status_field = "mo_survey_status"
    queryset = models.SurveyDetails.objects.select_related(
        "ilms_spare_id",
        "obs_spare_id",
        "vendor_id",
    )
    serializer_class = serializers.SurveyDetailsSerializer


@tagged_viewset("ILMS")
class PTSDetailsViewSet(ApprovalWorkflowMixin, ILMSModelViewSet):
    workflow_name = "PTS"
    completion_field = "is_pts"
    status_field = "mo_pts_status"
    queryset = models.PTSDetails.objects.select_related(
        "ilms_spare_id",
        "obs_spare_id",
        "vendor_id",
    )
    serializer_class = serializers.PTSDetailsSerializer


@tagged_viewset("ILMS")
class DemandDetailsViewSet(ApprovalWorkflowMixin, ILMSModelViewSet):
    workflow_name = "Demand"
    completion_field = "is_demand"
    status_field = "mo_status"
    queryset = models.DemandDetails.objects.select_related(
        "ilms_spare_id",
        "obs_spare_id",
        "vendor_id",
    )
    serializer_class = serializers.DemandDetailsSerializer

    @action(detail=True, methods=["post"], url_path="generate-number")
    def generate_number(self, request, pk=None):
        with transaction.atomic():
            demand = models.DemandDetails.objects.select_for_update().get(pk=pk)
            if not demand.is_hod_approval:
                raise ValidationError(
                    {
                        "detail": (
                            "HOD approval is required before generating "
                            "a demand number."
                        )
                    }
                )
            if not demand.demand_number:
                demand.demand_number = f"MO-DEMAND-{demand.pk:06d}"
                demand.is_demand = True
                demand.in_progress_status = "Demanded"
                demand.save(
                    update_fields=[
                        "demand_number",
                        "is_demand",
                        "in_progress_status",
                    ]
                )
        return Response(self.get_serializer(demand).data)

    @action(detail=False, methods=["get"], url_path="receive-queue")
    def receive_queue(self, request):
        queryset = self.get_queryset().exclude(demand_number="")
        return Response(self.get_serializer(queryset, many=True).data)

    @staticmethod
    def _receive_row(obj, source):
        planned_desc = (
            models.MOPlannedSparesDescription.objects.filter(item_id=obj.ilms_spare_id)
            .select_related("item_id")
            .first()
        )
        dart_number = "—"
        denomination = "—"
        crp_category = "—"
        quantity_required = "—"

        if planned_desc:
            if planned_desc.item_id:
                denomination = getattr(planned_desc.item_id, "item_deno", None) or "—"
                crp_category = (
                    getattr(planned_desc.item_id, "crp_category", None) or "—"
                )
            rd = _routine_description_summary(planned_desc.routine_description_id_id)
            if rd:
                dart_number = rd.get("dart_number") or "—"

        if obj.ilms_spare_id:
            planned_spare = models.PlannedMOSpareList.objects.filter(
                pattern_number=obj.ilms_spare_id.item_code
            ).first()
            if planned_spare:
                quantity_required = planned_spare.quantity_required

        if source == "Demand":
            return {
                "source": "Demand",
                "mo_item_code": (
                    obj.ilms_spare_id.item_code if obj.ilms_spare_id else "—"
                ),
                "item_description": (
                    obj.ilms_spare_id.item_desc if obj.ilms_spare_id else "—"
                ),
                "crp_category": crp_category,
                "denomination": (
                    obj.ilms_spare_id.item_deno if obj.ilms_spare_id else "-"
                ),
                "dart_number": dart_number,
                "demand_qty": quantity_required,
                "survey_number": "—",
                "qty_issued_by_mo": "—",
                "demand_number": obj.demand_number,
                "in_progress_status": obj.in_progress_status or "Pending",
            }

        return {
            "source": "Survey",
            "mo_item_code": obj.ilms_spare_id.item_code if obj.ilms_spare_id else "—",
            "item_description": (
                obj.ilms_spare_id.item_desc if obj.ilms_spare_id else "—"
            ),
            "crp_category": crp_category,
            "denomination": denomination,
            "dart_number": dart_number,
            "demand_qty": quantity_required,
            "survey_number": obj.demand_number,
            "qty_issued_by_mo": "—",
            "demand_number": obj.demand_number,
            "in_progress_status": obj.in_progress_status or "Pending",
        }

    @action(detail=False, methods=["get"], url_path="merged-receive-list")
    def merged_receive_list(self, request):
        demand_entries = (
            models.DemandDetails.objects.exclude(demand_number="")
            .filter(demand_number__isnull=False)
            .select_related("vendor_id", "ilms_spare_id")
        )
        survey_entries = (
            models.SurveyDetails.objects.exclude(demand_number="")
            .filter(demand_number__isnull=False)
            .select_related("vendor_id", "ilms_spare_id")
        )

        rows = [self._receive_row(obj, "Demand") for obj in demand_entries]
        rows += [self._receive_row(obj, "Survey") for obj in survey_entries]
        return Response({"entries": rows, "inventory_type": "mo"})

    @action(detail=False, methods=["get"])
    def consolidation(self, request):
        queryset = (
            self.get_queryset()
            .filter(is_demand=False)
            .values(
                "ilms_spare_id",
                "ilms_spare_id__item_desc",
                "vendor_id",
            )
            .annotate(record_count=Count("id"))
            .order_by("ilms_spare_id", "vendor_id")
        )
        return Response(
            [
                {
                    "item_code": entry["ilms_spare_id"],
                    "item_description": entry["ilms_spare_id__item_desc"],
                    "vendor_code": entry["vendor_id"],
                    "record_count": entry["record_count"],
                }
                for entry in queryset
            ]
        )


@tagged_viewset("ILMS")
class CustomerViewSet(ILMSModelViewSet):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerSerializer


@tagged_viewset("ILMS")
class ItemLineViewSet(ILMSModelViewSet):
    queryset = models.ItemLine.objects.select_related("item_code")
    serializer_class = serializers.ItemLineSerializer


@tagged_viewset("ILMS")
class CustomerEquipmentViewSet(ILMSModelViewSet):
    queryset = models.CustomerEquipment.objects.select_related(
        "customer",
        "equipment",
    )
    serializer_class = serializers.CustomerEquipmentSerializer


@tagged_viewset("ILMS")
class CustomerEquipmentLineViewSet(ILMSModelViewSet):
    queryset = models.CustomerEquipmentLine.objects.select_related(
        "customer",
        "equipment",
    )
    serializer_class = serializers.CustomerEquipmentLineSerializer


@tagged_viewset("ILMS")
class PriceViewSet(ILMSModelViewSet):
    queryset = models.Price.objects.select_related("item", "vendor")
    serializer_class = serializers.PriceSerializer


@tagged_viewset("ILMS")
class ItemIssuedViewSet(ILMSModelViewSet):
    queryset = models.ItemIssued.objects.select_related("customer", "item")
    serializer_class = serializers.ItemIssuedSerializer


@tagged_viewset("ILMS")
class IssuedDetailsViewSet(ILMSModelViewSet):
    queryset = models.IssuedDetails.objects.select_related("item")
    serializer_class = serializers.IssuedDetailsSerializer


@tagged_viewset("ILMS")
class ItemVendorViewSet(ILMSModelViewSet):
    queryset = models.ItemVendor.objects.select_related("item", "vendor")
    serializer_class = serializers.ItemVendorSerializer


@tagged_viewset("ILMS")
class ItemExtraViewSet(ILMSModelViewSet):
    queryset = models.ItemExtra.objects.select_related("item_deno")
    serializer_class = serializers.ItemExtraSerializer


@tagged_viewset("ILMS")
class VendorListViewSet(ILMSModelViewSet):
    queryset = models.VendorList.objects.all()
    serializer_class = serializers.VendorListSerializer


@tagged_viewset("ILMS")
class VendorPilViewSet(ILMSModelViewSet):
    queryset = models.VendorPil.objects.all()
    serializer_class = serializers.VendorPilSerializer


@tagged_viewset("ILMS")
class DartMOSpareViewSet(ILMSModelViewSet):
    queryset = models.DartMOSpare.objects.select_related(
        "issue_obj",
        "equipment_id",
        "dart_id",
        "mo_spare",
    )
    serializer_class = serializers.DartMOSpareSerializer


@tagged_viewset("ILMS")
class IIFViewSet(ILMSModelViewSet):
    queryset = models.IIF.objects.select_related("spare_id")
    serializer_class = serializers.IIFSerializer

    @extend_schema(request=serializers.AddToIIFCartSerializer)
    @action(detail=False, methods=["post"], url_path="add-items")
    def add_items(self, request):
        serializer = serializers.AddToIIFCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        spare_ids = serializer.validated_data["spare_ids"]

        from obs.models import Demand, Issue, Spares, Survey

        spares = list(Spares.objects.filter(pk__in=spare_ids))
        if len(spares) != len(set(spare_ids)):
            raise ValidationError(
                {"spare_ids": "One or more onboard spares were not found."}
            )

        created = []
        existing = []
        with transaction.atomic():
            for spare in spares:
                entry, was_created = models.IIF.objects.get_or_create(
                    spare_id=spare,
                    is_delete=False,
                    defaults={
                        "is_sync": False,
                        "sync_response": False,
                    },
                )
                (created if was_created else existing).append(entry)

                demand_issue_ids = Demand.objects.filter(
                    spare=spare,
                    is_iif=True,
                    issue_entry__isnull=False,
                ).values_list("issue_entry_id", flat=True)
                survey_issue_ids = Survey.objects.filter(
                    spare=spare,
                    is_iif=True,
                    issue_entry__isnull=False,
                ).values_list("issue_entry_id", flat=True)
                issue_ids = set(demand_issue_ids) | set(survey_issue_ids)
                if issue_ids:
                    Issue.objects.filter(pk__in=issue_ids).update(is_wed_mo=True)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            {
                "created": self.get_serializer(created, many=True).data,
                "existing": self.get_serializer(existing, many=True).data,
            },
            status=response_status,
        )

    @action(detail=True, methods=["post"], url_path="mark-synced")
    def mark_synced(self, request, pk=None):
        entry = self.get_object()
        entry.is_sync = True
        entry.sync_response = True
        entry.is_delete = True
        entry.save(update_fields=["is_sync", "sync_response", "is_delete"])
        return Response(self.get_serializer(entry).data)
