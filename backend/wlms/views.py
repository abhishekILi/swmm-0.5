import base64
import io

import pdfkit
import qrcode
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import models, serializers
from .excel import ExcelImportExportMixin
from .utils import tagged_viewset


def _zero_padded(value, width):
    return str(value).zfill(width)


def _next_ref_seq():
    year = timezone.localdate().year
    count = models.SurveyFormsDetails.objects.filter(created_date__year=year).count()
    return _zero_padded(count + 1, 3)


def _base_cert_offset():
    return models.SurveyFormsItems.objects.count()


def _generate_qr_b64(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _annotate_pending_wlms_entry(item, qty_field=None):
    """Attach dart_number/equipment_nomenclature/equipment_class/qty display
    fields to a Survey/Demand/PTS cart entry, matching the reference list views.
    """
    item.dart_number = ""
    item.dart_description = "-"
    item.equipment_nomenclature = ""
    item.equipment_class = "-"
    item.scrap_qty = getattr(item, qty_field, None) if qty_field else None
    item.scrap_qty = item.scrap_qty or "-"

    if item.wed_spares_id_id:
        dart_wed = None
        if item.wed_routine_plan_id:
            planned = item.wed_routine_plan
            rd = _routine_description_summary(planned.routine_description_id_id)
            if rd:
                item.dart_number = rd.get("dart_number") or ""
                item.dart_description = rd.get("routine_description") or "-"
                item.equipment_nomenclature = rd.get("equipment_name__name") or ""
        elif item.wed_dart_id:
            dart_wed = item.wed_dart
            if dart_wed.dart_id:
                item.dart_number = dart_wed.dart_id.dart_number or ""
                item.dart_description = dart_wed.dart_id.defective_discriptions or "-"
                if dart_wed.dart_id.equipment_ship:
                    item.equipment_nomenclature = (
                        dart_wed.dart_id.equipment_ship.nomenclature or ""
                    )

        if not qty_field or item.scrap_qty == "-":
            if item.wed_routine_plan_id:
                wed_spare_entry = models.PlannedWEDSpareList.objects.filter(
                    planned_spares_description=item.wed_routine_plan
                ).first()
                item.scrap_qty = (
                    wed_spare_entry.quantity_required
                    if wed_spare_entry and wed_spare_entry.quantity_required
                    else "-"
                )
            elif dart_wed and dart_wed.quantity:
                item.scrap_qty = dart_wed.quantity

        mapping = models.SpareDataMap.objects.filter(
            wed_equipment=item.wed_spares_id.eqpt
        ).first()
        if mapping and mapping.equipment:
            item.equipment_class = (
                getattr(mapping.equipment.equipment_type_f_key, "equipment_desc", None)
                or "-"
            )

    elif item.obs_spare_id_id:
        from dart.models import InitiateDart

        dart_obj = (
            InitiateDart.objects.filter(
                spares__pattern=item.obs_spare_id.pattern_number
            )
            .select_related("equipment_ship")
            .order_by("-id")
            .first()
        )
        if dart_obj:
            item.dart_number = dart_obj.dart_number or ""
            item.dart_description = dart_obj.defective_discriptions or "-"
            if dart_obj.equipment_ship:
                item.equipment_nomenclature = dart_obj.equipment_ship.nomenclature or ""

        if not qty_field or item.scrap_qty == "-":
            from obs.models import Survey as ObsSurvey

            survey_qty = (
                ObsSurvey.objects.filter(spare=item.obs_spare_id)
                .order_by("-id")
                .first()
            )
            if survey_qty:
                item.scrap_qty = survey_qty.quantity_tosurvey

    return item


def _expand_by_qty(base_item, qty, offset, idx_start):
    try:
        count = int(qty)
    except (TypeError, ValueError):
        count = 1

    expanded = []
    for i in range(count):
        row = dict(base_item)
        row["qty"] = 1
        row["cert_seq"] = _zero_padded(offset + idx_start + i, 4)
        expanded.append(row)
    return expanded


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


def _department_scoped(queryset, request):
    department_id = getattr(request.user, "department_id", None)
    if department_id:
        queryset = queryset.filter(user_id__department_id=department_id)
    return queryset


def _sync_wlms_rows(
    request,
    model,
    completion_field,
    status_field,
    ids,
    delete_after_sync=False,
):
    queryset = _department_scoped(
        model.objects.filter(is_sync=False, is_approval=True),
        request,
    )
    if ids:
        queryset = queryset.filter(pk__in=ids)

    sync_date = timezone.now()
    with transaction.atomic():
        rows = list(queryset.select_for_update())
        for row in rows:
            if completion_field:
                setattr(row, completion_field, True)
            row.is_sync = True
            row.sync_date = sync_date
            setattr(row, status_field, "Synced")
            if hasattr(row, "sync_response"):
                row.sync_response = True
            if delete_after_sync:
                row.is_delete = True

        update_fields = ["is_sync", "sync_date", status_field]
        if completion_field:
            update_fields.insert(0, completion_field)
        if rows and hasattr(rows[0], "sync_response"):
            update_fields.append("sync_response")
        if delete_after_sync:
            update_fields.append("is_delete")
        if rows:
            model.objects.bulk_update(rows, update_fields)

    return rows


@extend_schema(
    summary="WED common API sync",
    description=(
        "Marks approved-but-unsynced Survey/PTS/Demand/IIF cart entries as synced. "
        "This is a local, department-scoped operation only — it does not call the "
        "external legacy WLMS_IP service, which is not reachable from this "
        "deployment."
    ),
    tags=["WLMS"],
)
@api_view(["GET", "POST"])
def send_wed_common_api(request):
    ids = _extract_sync_ids(request)
    synced = {
        "survey": _sync_wlms_rows(
            request,
            models.SurveyReceiptsDetails,
            "is_survey",
            "wlms_survey_status",
            ids,
        ),
        "pts": _sync_wlms_rows(
            request,
            models.PTSDemandDetails,
            "is_pts",
            "wlms_pts_status",
            ids,
        ),
        "demand": _sync_wlms_rows(
            request,
            models.DemandDetails,
            "is_demand",
            "wlms_demand_status",
            ids,
        ),
        "iif": _sync_wlms_rows(
            request,
            models.WEDIIF,
            None,
            "wlms_iif_status",
            ids,
            delete_after_sync=True,
        ),
    }
    total = sum(len(rows) for rows in synced.values())
    return Response(
        {
            "status": "success" if total else "warning",
            "message": (
                "Data processed successfully"
                if total
                else "No approved unsynced records found"
            ),
            "updated": total,
            "created": 0,
            "counts": {name: len(rows) for name, rows in synced.items()},
        }
    )


@extend_schema(summary="Sync equipment from WED", tags=["WLMS"])
@api_view(["POST"])
def sync_equipment_from_wed(request):
    return Response(
        {
            "status": "warning",
            "message": "External WED equipment source is not configured.",
            "created": 0,
            "updated": 0,
        }
    )


@extend_schema(summary="Sync spares from WED", tags=["WLMS"])
@api_view(["POST"])
def sync_spares_from_wed(request):
    return Response(
        {
            "status": "warning",
            "message": "External WED spares source is not configured.",
            "created": 0,
            "updated": 0,
        }
    )


@extend_schema(tags=["WLMS"])
class WLMSModelViewSet(ExcelImportExportMixin, viewsets.ModelViewSet):
    pass


class ApprovalWorkflowMixin:
    workflow_name = ""
    completion_field = ""
    status_field = ""

    @extend_schema(request=serializers.AddToWorkflowCartSerializer)
    @action(detail=False, methods=["post"], url_path="add-to-cart")
    def add_to_cart(self, request):
        serializer = serializers.AddToWorkflowCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = serializer.validated_data["source"]
        source_ids = serializer.validated_data["source_ids"]
        records = self._resolve_cart_records(source, source_ids)
        if len(records) != len(set(source_ids)):
            raise ValidationError(
                {"source_ids": "One or more source records were not found."}
            )

        created_entries = []
        existing_entries = []
        with transaction.atomic():
            for record in records:
                lookup = {
                    "user_id": request.user,
                    "wed_spares_id": record["wed_spares_id"],
                    "obs_spare_id": record["obs_spare_id"],
                    "wed_routine_plan": record["wed_routine_plan"],
                    "wed_dart": record["wed_dart"],
                }
                defaults = {"spare_cart_name": self.workflow_name}
                if hasattr(self.queryset.model, "demand_qty"):
                    defaults["demand_qty"] = str(record["quantity"])
                entry, was_created = self.get_queryset().get_or_create(
                    **lookup,
                    defaults=defaults,
                )
                target = created_entries if was_created else existing_entries
                target.append(entry)

                if self.workflow_name == "Survey" and record["obs_spare_id"]:
                    self._flip_return_issue_to_wed_mo(record["obs_spare_id"])

        response_status = (
            status.HTTP_201_CREATED if created_entries else status.HTTP_200_OK
        )
        return Response(
            {
                "created": self.get_serializer(
                    created_entries,
                    many=True,
                ).data,
                "existing": self.get_serializer(
                    existing_entries,
                    many=True,
                ).data,
            },
            status=response_status,
        )

    def _flip_return_issue_to_wed_mo(self, obs_spare):
        from obs.models import Issue as ObsIssue
        from obs.models import Survey as ObsSurvey

        survey_entry = ObsSurvey.objects.filter(spare=obs_spare).order_by("-id").first()
        dart_number = survey_entry.dart_number if survey_entry else None
        return_issue = (
            ObsIssue.objects.filter(
                spare=obs_spare,
                dart_number=dart_number,
                is_return=True,
            )
            .order_by("-id")
            .first()
        )
        if return_issue:
            return_issue.is_wed_mo = True
            return_issue.is_deleted = True
            return_issue.save(update_fields=["is_wed_mo", "is_deleted"])

    def _resolve_cart_records(self, source, source_ids):
        if source == "planned":
            entries = models.PlannedWEDSpareList.objects.filter(
                pk__in=source_ids,
                is_deleted=False,
                planned_spares_description__is_deleted=False,
            ).select_related("planned_spares_description__wlms_spare_id")
            return [
                {
                    "wed_spares_id": (entry.planned_spares_description.wlms_spare_id),
                    "obs_spare_id": None,
                    "wed_routine_plan": (entry.planned_spares_description),
                    "wed_dart": None,
                    "quantity": entry.quantity_required,
                }
                for entry in entries
                if entry.planned_spares_description.wlms_spare_id
            ]
        if source == "dart":
            entries = models.DartWedSpare.objects.filter(
                pk__in=source_ids,
                is_delete=False,
            ).select_related("wed_spare")
            return [
                {
                    "wed_spares_id": entry.wed_spare,
                    "obs_spare_id": None,
                    "wed_routine_plan": None,
                    "wed_dart": entry,
                    "quantity": entry.quantity,
                }
                for entry in entries
                if entry.wed_spare
            ]

        from obs.models import Spares

        return [
            {
                "wed_spares_id": None,
                "obs_spare_id": spare,
                "wed_routine_plan": None,
                "wed_dart": None,
                "quantity": 1,
            }
            for spare in Spares.objects.filter(pk__in=source_ids)
        ]

    @action(detail=True, methods=["post"], url_path="send-for-approval")
    def send_for_approval(self, request, pk=None):
        entry = self.get_object()
        if entry.is_approval:
            raise ValidationError(
                {"detail": "Approved records cannot be submitted again."}
            )
        entry.is_hod = True
        entry.spare_cart_name = self.workflow_name
        update_fields = ["is_hod", "spare_cart_name"]
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
        queryset = self.get_queryset().filter(pk__in=ids, is_approval=False)
        update_kwargs = {
            "is_hod": True,
            "spare_cart_name": self.workflow_name,
        }
        if self.status_field:
            update_kwargs[self.status_field] = "Pending HOD Approval"
        updated = queryset.update(**update_kwargs)
        return Response({"success": True, "updated": updated})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_hod:
            raise ValidationError({"detail": "Record must be submitted to HOD first."})
        entry.is_approval = True
        update_fields = ["is_approval"]
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
        queryset = self.get_queryset().filter(
            pk__in=ids,
            is_hod=True,
            is_approval=False,
        )
        update_kwargs = {"is_approval": True}
        if self.status_field:
            update_kwargs[self.status_field] = "Approved"
        updated = queryset.update(**update_kwargs)
        return Response({"success": True, "updated": updated})

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        queryset = self.get_queryset().filter(
            is_hod=True,
            is_approval=False,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def outbox(self, request):
        queryset = self.get_queryset().filter(
            is_hod=True,
            is_approval=True,
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"], url_path="mark-synced")
    def mark_synced(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_approval:
            raise ValidationError(
                {"detail": "HOD approval is required before marking it synced."}
            )
        setattr(entry, self.completion_field, True)
        entry.is_sync = True
        update_fields = [self.completion_field, "is_sync"]
        if hasattr(entry, "sync_date"):
            entry.sync_date = timezone.now()
            update_fields.append("sync_date")
        if self.status_field:
            setattr(entry, self.status_field, "Synced")
            update_fields.append(self.status_field)
        entry.save(update_fields=update_fields)
        return Response(self.get_serializer(entry).data)

    def _pending_annotated_entries(self, request, qty_field):
        pending = (
            self.get_queryset()
            .select_related(
                "wed_spares_id__eqpt",
                "obs_spare_id",
                "wed_routine_plan",
                "wed_dart__dart_id__equipment_ship",
            )
            .order_by("-id")
        )
        if self.status_field:
            pending = pending.exclude(**{self.status_field: "Approved"})

        allowed_equipment_class_ids = _scoped_equipment_class_ids(request)
        pending = pending.filter(
            Q(wed_routine_plan__isnull=False)
            | Q(wed_dart__isnull=False)
            | Q(obs_spare_id__equipment_class_id__in=allowed_equipment_class_ids)
        )
        department_id = request.user.department_id
        if department_id:
            pending = pending.filter(user_id__department_id=department_id)

        return [
            _annotate_pending_wlms_entry(item, qty_field=qty_field) for item in pending
        ]

    def _serialize_pending(self, items):
        data = []
        for item in items:
            row = self.get_serializer(item).data
            for field in (
                "scrap_qty",
                "equipment_nomenclature",
                "dart_number",
                "dart_description",
                "equipment_class",
            ):
                row[field] = getattr(item, field, "-")
            data.append(row)
        return data


@tagged_viewset("WLMS")
class WLMSEquipmentViewSet(WLMSModelViewSet):
    queryset = models.WLMSEquipment.objects.all()
    serializer_class = serializers.WLMSEquipmentSerializer

    @action(detail=False, methods=["get"], url_path="insma-equipment")
    def insma_equipment(self, request):
        from sfd.models import ShipEquipment

        equipment = (
            ShipEquipment.objects.filter(status__iexact="active")
            .exclude(nomenclature__isnull=True)
            .values("id", "nomenclature")
            .distinct()
        )
        return Response(
            [
                {"id": entry["id"], "name": entry["nomenclature"] or "N/A"}
                for entry in equipment
            ]
        )

    @action(detail=False, methods=["get"], url_path="unmapped")
    def unmapped(self, request):
        mapped_ids = models.SpareDataMap.objects.values_list(
            "wed_equipment_id", flat=True
        )
        equipment = self.get_queryset().exclude(id__in=mapped_ids)
        return Response(self.get_serializer(equipment, many=True).data)


@tagged_viewset("WLMS")
class WLMSSpareViewSet(WLMSModelViewSet):
    queryset = models.WLMSSpare.objects.select_related("eqpt")
    serializer_class = serializers.WLMSSpareSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        equipment_id = self.request.query_params.get("equipment_id")
        query = self.request.query_params.get("q")
        active = self.request.query_params.get("active")
        if equipment_id:
            queryset = queryset.filter(eqpt_id=equipment_id)
        if query:
            queryset = queryset.filter(
                Q(item_code__icontains=query)
                | Q(item_desc__icontains=query)
                | Q(eqpt__eqpt_name__icontains=query)
                | Q(category__icontains=query)
            )
        if active is not None:
            queryset = queryset.filter(is_active=active.lower() in {"1", "true", "yes"})
        return queryset

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        active_spares = models.WLMSSpare.objects.filter(is_active=True)
        return Response(
            {
                "equipment": models.WLMSEquipment.objects.filter(
                    is_active=True
                ).count(),
                "active_spares": active_spares.count(),
                "available_quantity": (
                    active_spares.aggregate(total=Sum("latest_qty"))["total"] or 0
                ),
                "pending_surveys": models.SurveyReceiptsDetails.objects.filter(
                    is_survey=False
                ).count(),
                "pending_pts": models.PTSDemandDetails.objects.filter(
                    is_pts=False
                ).count(),
                "pending_demands": models.DemandDetails.objects.filter(
                    is_demand=False,
                    is_delete=False,
                ).count(),
                "pending_iif": models.WEDIIF.objects.filter(
                    is_sync=False,
                    is_delete=False,
                ).count(),
            }
        )

    @action(detail=False, methods=["get"], url_path="equipment-list")
    def equipment_list(self, request):
        queryset = models.WLMSEquipment.objects.all()
        if request.query_params.get("active") is not None:
            queryset = queryset.filter(
                is_active=request.query_params["active"].lower() in {"1", "true", "yes"}
            )
        return Response(serializers.WLMSEquipmentSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="by-equipment")
    def by_equipment(self, request):
        equipment_id = request.query_params.get("equipment_id")
        if not equipment_id:
            raise ValidationError({"equipment_id": "This query parameter is required."})
        queryset = self.get_queryset().filter(eqpt_id=equipment_id)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="equipment-for-spares")
    def equipment_for_spares(self, request):
        spare_ids = request.query_params.getlist("spare_ids")
        if not spare_ids:
            raise ValidationError({"spare_ids": "This query parameter is required."})

        spares = self.get_queryset().filter(pk__in=spare_ids)
        equipment_data = {}
        for spare in spares:
            equipment_data[str(spare.pk)] = {"equipment_id": "", "equipment_code": ""}
            if not spare.eqpt_id:
                continue
            mapping = (
                models.SpareDataMap.objects.filter(
                    wed_equipment=spare.eqpt,
                    equipment__isnull=False,
                )
                .select_related("equipment")
                .first()
            )
            if mapping and mapping.equipment:
                equipment_data[str(spare.pk)] = {
                    "equipment_id": str(mapping.equipment_id),
                    "equipment_code": mapping.equipment.equipment_code or "",
                }
        return Response({"equipment_data": equipment_data})

    @action(detail=True, methods=["get"])
    def context(self, request, pk=None):
        spare = self.get_object()
        equipment_mappings = models.SpareDataMap.objects.filter(
            wed_equipment=spare.eqpt
        ).select_related("equipment", "wed_equipment")
        surveys = models.SurveyReceiptsDetails.objects.filter(wed_spares_id=spare)
        pts_entries = models.PTSDemandDetails.objects.filter(wed_spares_id=spare)
        demands = models.DemandDetails.objects.filter(wed_spares_id=spare)
        receipts = models.ReceiveDemandDetails.objects.filter(
            demand_details__wed_spares_id=spare
        )
        return Response(
            {
                "spare": self.get_serializer(spare).data,
                "equipment_mappings": serializers.SpareDataMapSerializer(
                    equipment_mappings,
                    many=True,
                ).data,
                "surveys": serializers.SurveyReceiptsDetailsSerializer(
                    surveys,
                    many=True,
                ).data,
                "pts": serializers.PTSDemandDetailsSerializer(
                    pts_entries,
                    many=True,
                ).data,
                "demands": serializers.DemandDetailsSerializer(
                    demands,
                    many=True,
                ).data,
                "receipts": serializers.ReceiveDemandDetailsSerializer(
                    receipts,
                    many=True,
                ).data,
            }
        )

    def context_from_query(self, request):
        spare_id = (
            request.query_params.get("spare_id")
            or request.query_params.get("spare")
            or request.query_params.get("pk")
            or request.query_params.get("id")
        )
        if not spare_id:
            raise ValidationError({"spare_id": "This query parameter is required."})
        self.kwargs[self.lookup_url_kwarg or self.lookup_field] = spare_id
        return self.context(request, pk=spare_id)

    @action(detail=True, methods=["get"], url_path="routine-context")
    def routine_context(self, request, pk=None):
        spare = self.get_object()
        mapping = (
            models.SpareDataMap.objects.filter(
                wed_equipment=spare.eqpt,
                equipment__isnull=False,
            )
            .select_related("equipment")
            .first()
        )
        planned = models.PlannedSparesDescription.objects.filter(
            wlms_spare_id=spare,
            is_deleted=False,
        ).first()
        return Response(
            {
                "mapped": mapping is not None,
                "ship_equipment_id": (mapping.equipment_id if mapping else None),
                "routine_description_id": (
                    planned.routine_description_id_id if planned else None
                ),
            }
        )


@tagged_viewset("WLMS")
class SpareDataMapViewSet(WLMSModelViewSet):
    queryset = models.SpareDataMap.objects.select_related(
        "equipment",
        "wed_equipment",
    ).all()
    serializer_class = serializers.SpareDataMapSerializer

    @action(detail=False, methods=["get"], url_path="sfd-equipment-for-wed")
    def sfd_equipment_for_wed(self, request):
        wed_equipment = request.query_params.get("wed_equipment")
        if not wed_equipment:
            raise ValidationError(
                {"wed_equipment": "This query parameter is required."}
            )
        queryset = self.get_queryset().filter(wed_equipment_id=wed_equipment)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="obs-spare-class")
    def obs_spare_class(self, request):
        from obs.models import SpareClass
        from sfd.models import ShipEquipment

        equipment_id = request.query_params.get("equipment_id")
        queryset = SpareClass.objects.select_related("department").distinct("name")
        if equipment_id:
            ship_equipment = ShipEquipment.objects.filter(pk=equipment_id).first()
            if ship_equipment and ship_equipment.department_id:
                queryset = queryset.filter(department_id=ship_equipment.department_id)
        return Response([{"id": entry.id, "name": entry.name} for entry in queryset])


@tagged_viewset("WLMS")
class PlannedSparesDescriptionViewSet(WLMSModelViewSet):
    queryset = models.PlannedSparesDescription.objects.select_related(
        "wlms_spare_id",
    ).all()
    serializer_class = serializers.PlannedSparesDescriptionSerializer


@tagged_viewset("WLMS")
class PlannedWEDSpareListViewSet(WLMSModelViewSet):
    queryset = models.PlannedWEDSpareList.objects.select_related(
        "planned_spares_description__wlms_spare_id",
    )
    serializer_class = serializers.PlannedWEDSpareListSerializer

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
        url_path="check-routine-mapping",
    )
    def check_routine_mapping(self, request):
        from ems.models import RoutineDescription

        spare_ids = request.query_params.getlist("spare_ids")
        if not spare_ids:
            raise ValidationError({"spare_ids": "At least one spare id is required."})

        unmapped = []
        spares = {}
        for spare_id in spare_ids:
            spare = (
                models.WLMSSpare.objects.select_related("eqpt")
                .filter(pk=spare_id)
                .first()
            )
            if not spare:
                unmapped.append(f"Spare ID {spare_id}")
                continue
            spares[spare_id] = spare
            is_mapped = models.SpareDataMap.objects.filter(
                wed_equipment=spare.eqpt
            ).exists()
            if not is_mapped:
                unmapped.append(
                    spare.eqpt.eqpt_name if spare.eqpt else f"Spare ID {spare_id}"
                )

        if unmapped:
            return Response(
                {
                    "status": "error",
                    "message": (
                        f"Equipment not mapped: {', '.join(unmapped)}. "
                        "Please go to Master and map it first."
                    ),
                }
            )

        first_spare = spares[spare_ids[0]]
        mapping = models.SpareDataMap.objects.filter(
            wed_equipment=first_spare.eqpt
        ).first()
        planned = models.PlannedSparesDescription.objects.filter(
            wlms_spare_id__eqpt=first_spare.eqpt
        ).first()

        target_id = None
        if planned and planned.routine_description_id_id:
            target_id = planned.routine_description_id_id
        elif mapping and mapping.equipment_id:
            routine = (
                RoutineDescription.objects.filter(
                    equipment_name__sfd_equipment__id=mapping.equipment_id
                )
                .values("id")
                .first()
            )
            if routine:
                target_id = routine["id"]

        if target_id:
            return Response(
                {
                    "status": "success",
                    "routine_description_id": target_id,
                    "spare_ids": spare_ids,
                }
            )
        return Response({"status": "error", "message": "No mapping found."})


@extend_schema_view(
    list=extend_schema(
        examples=[
            OpenApiExample(
                "DART WED spare response",
                value=[
                    {
                        "id": 1,
                        "equipment_id": 501,
                        "dart_id": 1001,
                        "pattern": "WED-PN-1001",
                        "description": "Launcher interface module for DART",
                        "quantity": 1,
                        "created_date": "2026-06-02",
                        "modified_date": "2026-06-02",
                        "is_delete": False,
                        "issue_obj": 1,
                        "wed_spare": 1,
                    }
                ],
                response_only=True,
            )
        ]
    ),
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Create DART WED spare",
                value={
                    "equipment_id": 501,
                    "dart_id": 1001,
                    "pattern": "WED-PN-1001",
                    "description": "Launcher interface module for DART",
                    "quantity": 1,
                    "is_delete": False,
                    "issue_obj": 1,
                    "wed_spare": 1,
                },
                request_only=True,
            )
        ]
    ),
)
@tagged_viewset("WLMS")
class DartWedSpareViewSet(WLMSModelViewSet):
    queryset = models.DartWedSpare.objects.select_related(
        "dart_id",
        "equipment_id",
        "issue_obj",
        "wed_spare",
    ).all()
    serializer_class = serializers.DartWedSpareSerializer


@tagged_viewset("WLMS")
class SurveyReceiptsDetailsViewSet(
    ApprovalWorkflowMixin,
    WLMSModelViewSet,
):
    workflow_name = "Survey"
    completion_field = "is_survey"
    status_field = "wlms_survey_status"
    queryset = models.SurveyReceiptsDetails.objects.all()
    serializer_class = serializers.SurveyReceiptsDetailsSerializer

    @action(detail=False, methods=["get"], url_path="pending-list")
    def pending_list(self, request):
        items = self._pending_annotated_entries(request, qty_field=None)
        for item in items:
            survey_form = models.SurveyFormsDetails.objects.filter(
                survey_rec_id=item
            ).first()
            if survey_form and survey_form.scrap_qty:
                item.scrap_qty = survey_form.scrap_qty

        completed = (
            self.get_queryset()
            .filter(is_hod=True)
            .select_related("wed_spares_id__eqpt", "obs_spare_id")
            .order_by("-id")
        )
        department_id = request.user.department_id
        if department_id:
            completed = completed.filter(user_id__department_id=department_id)

        return Response(
            {
                "pending_surveys": self._serialize_pending(items),
                "completed_surveys": self.get_serializer(completed, many=True).data,
            }
        )

    @action(detail=False, methods=["get"], url_path="edps-pdf")
    def edps_pdf(self, request):
        pk_list = [
            pk.strip()
            for pk in request.query_params.get("survey_pks", "").split(",")
            if pk.strip()
        ]
        if not pk_list:
            return HttpResponse("No survey PKs supplied.", status=400)

        surveys = list(
            models.SurveyReceiptsDetails.objects.filter(pk__in=pk_list).select_related(
                "wed_spares_id__eqpt"
            )
        )
        if not surveys:
            return HttpResponse("No matching surveys found.", status=404)

        first_survey = surveys[0]
        form_entry = (
            models.SurveyFormsDetails.objects.filter(survey_rec_id=first_survey)
            .order_by("id")
            .first()
        )

        offset = _base_cert_offset()
        today_str = timezone.localdate().strftime("%d%m%Y")
        items = []

        if form_entry:
            item_rows = models.SurveyFormsItems.objects.filter(
                survey_details_id=form_entry
            ).select_related("wed_spares_id__eqpt")

            for idx, sfi in enumerate(item_rows, start=1):
                spare = sfi.wed_spares_id
                eqpt = getattr(spare, "eqpt", None) if spare else None

                qty = ""
                if spare:
                    qty = (
                        models.PlannedWEDSpareList.objects.filter(
                            planned_spares_description__wlms_spare_id=spare
                        )
                        .values_list("quantity_required", flat=True)
                        .first()
                    )
                    if not qty:
                        survey_receipt = models.SurveyReceiptsDetails.objects.filter(
                            wed_spares_id=spare
                        ).first()
                        if survey_receipt and survey_receipt.obs_spare_id:
                            from obs.models import Survey as ObsSurvey

                            survey_qty = (
                                ObsSurvey.objects.filter(
                                    spare=survey_receipt.obs_spare_id
                                )
                                .order_by("-id")
                                .first()
                            )
                            if survey_qty:
                                qty = survey_qty.quantity_tosurvey
                    if not qty:
                        dart_wed = (
                            models.DartWedSpare.objects.filter(wed_spare=spare)
                            .select_related("dart_id")
                            .first()
                        )
                        if dart_wed and dart_wed.quantity:
                            qty = dart_wed.quantity
                    qty = qty or ""

                items.append(
                    {
                        "ship_name": "INS KOCHI",
                        "survey_type": form_entry.held_certificate_type or "",
                        "from_field": "-",
                        "equipment_name": (
                            getattr(eqpt, "eqpt_name", "") if eqpt else ""
                        ),
                        "part_no": getattr(spare, "item_code", "") if spare else "",
                        "item_desc": getattr(spare, "item_desc", "") if spare else "",
                        "denomination": (
                            getattr(spare, "denom_id", "") if spare else ""
                        ),
                        "qty": 1,
                        "category": getattr(spare, "category", "") if spare else "",
                        "item_serial_no": sfi.item_serial_no or "",
                        "cert_seq": _zero_padded(offset + idx, 4),
                    }
                )
        else:
            global_idx = 1
            for survey in surveys:
                spare = survey.wed_spares_id
                eqpt = getattr(spare, "eqpt", None) if spare else None

                qty = ""
                if spare:
                    qty = (
                        models.PlannedWEDSpareList.objects.filter(
                            planned_spares_description__wlms_spare_id=spare,
                            is_deleted=False,
                        )
                        .values_list("quantity_required", flat=True)
                        .first()
                        or ""
                    )

                base_item = {
                    "ship_name": "INS KOCHI",
                    "survey_type": "",
                    "from_field": "",
                    "equipment_name": getattr(eqpt, "eqpt_name", "") if eqpt else "",
                    "part_no": getattr(spare, "item_code", "") if spare else "",
                    "item_desc": getattr(spare, "item_desc", "") if spare else "",
                    "denomination": getattr(spare, "denom_id", "") if spare else "",
                    "category": getattr(spare, "category", "") if spare else "",
                    "item_serial_no": (
                        getattr(spare, "wlms_inventory", "") if spare else ""
                    ),
                }
                expanded = _expand_by_qty(base_item, qty, offset, global_idx)
                items.extend(expanded)
                global_idx += len(expanded)

        hod_personal_no = request.query_params.get("hod_personal_no", "").strip()
        if not hod_personal_no:
            hod_personal_no = getattr(request.user, "personnel_number", "") or ""
        hod_qr_b64 = _generate_qr_b64(hod_personal_no) if hod_personal_no else ""

        context = {
            "items": items,
            "current_year": timezone.localdate().year,
            "ref_seq": _next_ref_seq(),
            "current_date": today_str,
            "form_entry": form_entry,
            "hod_personal_no": hod_personal_no,
            "hod_qr_b64": hod_qr_b64,
        }
        html_string = render_to_string("wlms_edps_survey.html", context)

        options = {
            "page-size": "A4",
            "orientation": "Landscape",
            "margin-top": "15mm",
            "margin-right": "12mm",
            "margin-bottom": "15mm",
            "margin-left": "12mm",
            "encoding": "UTF-8",
            "no-outline": None,
            "enable-local-file-access": None,
            "quiet": "",
        }
        pdf = pdfkit.from_string(html_string, False, options=options)

        filename = f"EDPS3_ReturnNote_{timezone.localdate().strftime('%Y%m%d')}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


@tagged_viewset("WLMS")
class SurveyFormsDetailsViewSet(WLMSModelViewSet):
    queryset = models.SurveyFormsDetails.objects.all()
    serializer_class = serializers.SurveyFormsDetailsSerializer

    @action(detail=True, methods=["post"], url_path="generate-number")
    def generate_number(self, request, pk=None):
        with transaction.atomic():
            form = self.get_queryset().select_for_update().get(pk=pk)
            survey = form.survey_rec_id
            if survey is None or not survey.is_approval:
                raise ValidationError(
                    {
                        "detail": (
                            "HOD approval is required before generating "
                            "a survey number."
                        )
                    }
                )
            if not form.survey_no:
                form.survey_no = f"SWMM/SURVEY/{timezone.now().year}/{form.pk:03d}"
                form.save(update_fields=["survey_no"])
            if not survey.is_survey:
                survey.is_survey = True
                survey.save(update_fields=["is_survey"])
        return Response(self.get_serializer(form).data)


@tagged_viewset("WLMS")
class SurveyFormsItemsViewSet(WLMSModelViewSet):
    queryset = models.SurveyFormsItems.objects.all()
    serializer_class = serializers.SurveyFormsItemsSerializer


@tagged_viewset("WLMS")
class PTSItemsViewSet(WLMSModelViewSet):
    queryset = models.PTSItems.objects.all()
    serializer_class = serializers.PTSItemsSerializer


@tagged_viewset("WLMS")
class PTSDemandDetailsViewSet(ApprovalWorkflowMixin, WLMSModelViewSet):
    workflow_name = "PTS"
    completion_field = "is_pts"
    status_field = "wlms_pts_status"
    queryset = models.PTSDemandDetails.objects.all()
    serializer_class = serializers.PTSDemandDetailsSerializer

    @action(detail=False, methods=["get"], url_path="pending-list")
    def pending_list(self, request):
        items = self._pending_annotated_entries(request, qty_field="demand_qty")
        return Response({"pending_pts": self._serialize_pending(items)})

    @action(detail=True, methods=["post"], url_path="generate-number")
    def generate_number(self, request, pk=None):
        with transaction.atomic():
            pts = self.get_queryset().select_for_update().get(pk=pk)
            if not pts.is_approval:
                raise ValidationError(
                    {
                        "detail": (
                            "HOD approval is required before generating a PTS number."
                        )
                    }
                )
            if not pts.PTS_demand_no:
                pts.PTS_demand_no = f"SWMM/PTS/{timezone.now().year}/{pts.pk:03d}"
                pts.is_pts = True
                pts.save(update_fields=["PTS_demand_no", "is_pts"])
        return Response(self.get_serializer(pts).data)


@tagged_viewset("WLMS")
class DemandDetailsViewSet(ApprovalWorkflowMixin, WLMSModelViewSet):
    workflow_name = "Demand"
    completion_field = "is_demand"
    status_field = "wlms_demand_status"
    queryset = models.DemandDetails.objects.all()
    serializer_class = serializers.DemandDetailsSerializer

    @action(detail=False, methods=["get"], url_path="pending-list")
    def pending_list(self, request):
        items = self._pending_annotated_entries(request, qty_field="demand_qty")
        return Response({"pending_demands": self._serialize_pending(items)})

    @action(detail=True, methods=["post"], url_path="generate-number")
    def generate_number(self, request, pk=None):
        with transaction.atomic():
            demand = self.get_queryset().select_for_update().get(pk=pk)
            if not demand.is_approval:
                raise ValidationError(
                    {
                        "detail": (
                            "HOD approval is required before generating "
                            "a demand number."
                        )
                    }
                )
            if not demand.demand_no:
                demand.demand_no = f"SWMM/DEMAND/{timezone.now().year}/{demand.pk:03d}"
                demand.is_demand = True
                demand.save(update_fields=["demand_no", "is_demand"])
        return Response(self.get_serializer(demand).data)

    @action(detail=False, methods=["get"], url_path="receive-queue")
    def receive_queue(self, request):
        queryset = (
            self.get_queryset()
            .exclude(demand_no="")
            .exclude(receivedemanddetails__demand_status__iexact="received")
            .distinct()
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def consolidation(self, request):
        pending = (
            self.get_queryset()
            .filter(
                is_demand=False,
                is_delete=False,
                wed_spares_id__isnull=False,
            )
            .select_related("wed_spares_id")
        )
        grouped = {}
        for demand in pending:
            key = demand.wed_spares_id_id
            if key not in grouped:
                grouped[key] = {
                    "item_code": demand.wed_spares_id.item_code,
                    "item_description": demand.wed_spares_id.item_desc,
                    "record_count": 0,
                    "total_quantity": 0,
                }
            grouped[key]["record_count"] += 1
            try:
                grouped[key]["total_quantity"] += int(demand.demand_qty)
            except (TypeError, ValueError):
                pass
        return Response(list(grouped.values()))


@extend_schema_view(
    list=extend_schema(
        examples=[
            OpenApiExample(
                "Receive demand response",
                value=[
                    {
                        "id": 1,
                        "demand_number": "WLMS-DEM-001",
                        "demand_date": "2026-06-03",
                        "demand_quantity": 5,
                        "demand_status": "received",
                        "swmm_demandno": "SWMM-DEM-001",
                        "dart_no": "DART-001",
                        "created_at": "2026-06-03T10:00:00Z",
                        "updated_at": "2026-06-03T10:00:00Z",
                        "gate_pass_no": "GP-001",
                        "gate_pass_date": "2026-06-03T10:00:00Z",
                        "demand_details": None,
                    }
                ],
                response_only=True,
            )
        ]
    ),
    create=extend_schema(
        examples=[
            OpenApiExample(
                "Create receive demand",
                value={
                    "demand_number": "WLMS-DEM-001",
                    "demand_date": "2026-06-03",
                    "demand_quantity": 5,
                    "demand_status": "received",
                    "swmm_demandno": "SWMM-DEM-001",
                    "dart_no": "DART-001",
                    "gate_pass_no": "GP-001",
                    "gate_pass_date": "2026-06-03T10:00:00Z",
                    "demand_details": None,
                },
                request_only=True,
            )
        ]
    ),
)
@tagged_viewset("WLMS")
class ReceiveDemandDetailsViewSet(WLMSModelViewSet):
    queryset = models.ReceiveDemandDetails.objects.all()
    serializer_class = serializers.ReceiveDemandDetailsSerializer

    def perform_create(self, serializer):
        demand = serializer.validated_data.get("demand_details")
        quantity = serializer.validated_data.get("demand_quantity", 0)
        demand_status = serializer.validated_data.get("demand_status", "")
        if demand is None:
            raise ValidationError({"demand_details": "A valid demand is required."})
        if demand_status.lower() != "received":
            serializer.save()
            return

        with transaction.atomic():
            locked_demand = models.DemandDetails.objects.select_for_update().get(
                pk=demand.pk
            )
            if models.ReceiveDemandDetails.objects.filter(
                demand_details=locked_demand,
                demand_status__iexact="received",
            ).exists():
                raise ValidationError(
                    {"demand_details": "This demand is already received."}
                )
            if not locked_demand.wed_spares_id:
                raise ValidationError(
                    {
                        "demand_details": (
                            "Demand is not linked to a WED inventory spare."
                        )
                    }
                )
            spare = models.WLMSSpare.objects.select_for_update().get(
                pk=locked_demand.wed_spares_id_id
            )
            models.WLMSSpare.objects.filter(pk=spare.pk).update(
                latest_qty=F("latest_qty") + quantity
            )
            serializer.save(demand_details=locked_demand)


@tagged_viewset("WLMS")
class WEDIIFViewSet(WLMSModelViewSet):
    queryset = models.WEDIIF.objects.all()
    serializer_class = serializers.WEDIIFSerializer

    @extend_schema(request=serializers.AddToIIFCartSerializer)
    @action(detail=False, methods=["post"], url_path="add-items")
    def add_items(self, request):
        serializer = serializers.AddToIIFCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        spare_ids = serializer.validated_data["spare_ids"]

        from obs.models import Spares

        spares = list(Spares.objects.filter(pk__in=spare_ids))
        if len(spares) != len(set(spare_ids)):
            raise ValidationError(
                {"spare_ids": "One or more onboard spares were not found."}
            )

        created = []
        existing = []
        with transaction.atomic():
            for spare in spares:
                entry, was_created = models.WEDIIF.objects.get_or_create(
                    spare_id=spare,
                    is_delete=False,
                    defaults={
                        "user_id": request.user,
                        "is_sync": False,
                        "is_hod": False,
                        "is_approval": False,
                        "sync_response": False,
                    },
                )
                (created if was_created else existing).append(entry)

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            {
                "created": self.get_serializer(created, many=True).data,
                "existing": self.get_serializer(existing, many=True).data,
            },
            status=response_status,
        )

    @action(detail=True, methods=["post"], url_path="send-for-approval")
    def send_for_approval(self, request, pk=None):
        entry = self.get_object()
        if entry.is_approval:
            raise ValidationError(
                {"detail": "Approved records cannot be submitted again."}
            )
        entry.is_hod = True
        entry.wlms_iif_status = "Pending HOD Approval"
        entry.save(update_fields=["is_hod", "wlms_iif_status"])
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_hod:
            raise ValidationError({"detail": "Record must be submitted to HOD first."})
        entry.is_approval = True
        entry.wlms_iif_status = "Approved"
        entry.save(update_fields=["is_approval", "wlms_iif_status"])
        return Response(self.get_serializer(entry).data)

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        queryset = self.get_queryset().filter(is_hod=True, is_approval=False)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def outbox(self, request):
        queryset = self.get_queryset().filter(is_hod=True, is_approval=True)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["post"], url_path="mark-synced")
    def mark_synced(self, request, pk=None):
        entry = self.get_object()
        if not entry.is_approval:
            raise ValidationError(
                {"detail": "HOD approval is required before marking it synced."}
            )
        entry.is_sync = True
        entry.sync_response = True
        entry.is_delete = True
        entry.sync_date = timezone.now()
        entry.wlms_iif_status = "Synced"
        entry.save(
            update_fields=[
                "is_sync",
                "sync_response",
                "is_delete",
                "sync_date",
                "wlms_iif_status",
            ]
        )
        return Response(self.get_serializer(entry).data)


@tagged_viewset("WLMS")
class WEDIIFDetailsViewSet(WLMSModelViewSet):
    queryset = models.WEDIIFDetails.objects.select_related("wed_iif").all()
    serializer_class = serializers.WEDIIFDetailsSerializer

    def _get_or_create_for_wed_iif(self, wed_iif_pk):
        wed_iif = models.WEDIIF.objects.filter(
            pk=wed_iif_pk,
            is_delete=False,
        ).first()
        if wed_iif is None:
            raise ValidationError({"detail": "WED IIF record not found."})
        details, _created = models.WEDIIFDetails.objects.get_or_create(
            wed_iif=wed_iif,
            defaults={
                "iif_no": (f"SWMM/IIF/{timezone.now().year}/{wed_iif.pk:03d}"),
            },
        )
        return details

    def retrieve(self, request, *args, **kwargs):
        details = self._get_or_create_for_wed_iif(kwargs["pk"])
        return Response(self.get_serializer(details).data)

    def update(self, request, *args, **kwargs):
        details = self._get_or_create_for_wed_iif(kwargs["pk"])
        serializer = self.get_serializer(details, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


@tagged_viewset("WLMS")
class SignalDemandViewSet(WLMSModelViewSet):
    queryset = models.SignalDemand.objects.select_related(
        "requesting_ship",
        "receiver_ship",
        "equipment",
        "wed_spare",
        "obs_spare",
        "created_by",
    )
    serializer_class = serializers.SignalDemandSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        demand_type = self.request.query_params.get("demand_type")
        demand_status = self.request.query_params.get("status")
        ship = self.request.query_params.get("ship")
        query = self.request.query_params.get("q")

        if demand_type:
            queryset = queryset.filter(demand_type=demand_type.upper())
        if demand_status:
            queryset = queryset.filter(status=demand_status.upper())
        if ship:
            queryset = queryset.filter(
                Q(requesting_ship_id=ship) | Q(receiver_ship_id=ship)
            )
        if query:
            queryset = queryset.filter(
                Q(demand_number__icontains=query)
                | Q(wed_spare__item_code__icontains=query)
                | Q(wed_spare__item_desc__icontains=query)
                | Q(obs_spare__pattern_number__icontains=query)
                | Q(obs_spare__description__icontains=query)
            )
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _change_status(self, demand, target_status, allowed_statuses):
        if demand.status not in allowed_statuses:
            raise ValidationError(
                {
                    "status": (
                        f"{demand.demand_type} cannot move from "
                        f"{demand.status} to {target_status}."
                    )
                }
            )
        demand.status = target_status
        demand.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(demand).data)

    @action(detail=True, methods=["post"])
    def forward(self, request, pk=None):
        return self._change_status(
            self.get_object(),
            models.SignalDemand.FORWARDED,
            {models.SignalDemand.REGISTERED},
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._change_status(
            self.get_object(),
            models.SignalDemand.APPROVED,
            {models.SignalDemand.FORWARDED},
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._change_status(
            self.get_object(),
            models.SignalDemand.REJECTED,
            {models.SignalDemand.FORWARDED},
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._change_status(
            self.get_object(),
            models.SignalDemand.CANCELLED,
            {
                models.SignalDemand.REGISTERED,
                models.SignalDemand.FORWARDED,
            },
        )


def _scoped_equipment_class_ids(request):
    from obs.models import EquipmentClass

    return EquipmentClass.objects.filter(
        spare_class__department_id=request.user.department_id
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
        )
        .first()
    )


def _annotate_wlms_cart_entry(entry):
    from dart.models import DartSpare
    from obs.models import Issue as ObsIssue

    entry.dart_number = "—"
    entry.equipment_name = "—"
    entry.routine_description = "—"
    entry.equipment_nomenclature = "—"
    entry.quantity_required = "—"
    entry.item_serial_no = getattr(entry, "item_serial_no", "—")

    try:
        if entry.obs_spare_id_id:
            dart_spare = (
                DartSpare.objects.filter(spare_id=entry.obs_spare_id_id)
                .select_related("dart", "dart__equipment_ship")
                .order_by("-id")
                .first()
            )
            if dart_spare and dart_spare.dart:
                dart_obj = dart_spare.dart
                entry.dart_number = dart_obj.dart_number or "—"
                entry.routine_description = dart_obj.defective_discriptions or "—"
                entry.equipment_nomenclature = (
                    dart_obj.equipment_ship.nomenclature
                    if dart_obj.equipment_ship
                    else "—"
                )
            issue_obj = (
                ObsIssue.objects.filter(spare_id=entry.obs_spare_id_id)
                .order_by("-id")
                .first()
            )
            entry.quantity_required = issue_obj.quantity_issued if issue_obj else "—"
        elif entry.wed_dart_id and entry.wed_dart.dart_id:
            dart_obj = entry.wed_dart.dart_id
            entry.dart_number = dart_obj.dart_number or "—"
            entry.routine_description = dart_obj.defective_discriptions or "—"
            entry.equipment_nomenclature = (
                dart_obj.equipment_ship.nomenclature if dart_obj.equipment_ship else "—"
            )
            entry.quantity_required = entry.wed_dart.quantity
        elif entry.wed_routine_plan_id:
            planned_desc = entry.wed_routine_plan
            rd = _routine_description_summary(
                planned_desc.routine_description_id_id if planned_desc else None
            )
            if rd:
                entry.dart_number = rd.get("dart_number") or "—"
                entry.equipment_name = rd.get("equipment_name__extra") or "—"
                entry.routine_description = rd.get("routine_description") or "—"
                entry.equipment_nomenclature = rd.get("equipment_name__name") or "—"
                planned_spare = models.PlannedWEDSpareList.objects.filter(
                    planned_spares_description=planned_desc
                ).first()
                entry.quantity_required = (
                    planned_spare.quantity_required if planned_spare else "—"
                )
    except Exception:
        entry.dart_number = "—"
        entry.equipment_name = "—"
        entry.routine_description = "—"
        entry.equipment_nomenclature = "—"
        entry.quantity_required = "—"
        entry.item_serial_no = getattr(entry, "item_serial_no", "—")

    return entry


@extend_schema(
    summary="Combined WLMS outbox",
    description=(
        "Merges HOD-submitted Survey, Demand, PTS and IIF cart entries into a "
        "single annotated list, matching the reference wlms_outbox view."
    ),
    tags=["WLMS"],
)
@api_view(["GET"])
def wlms_combined_outbox(request):
    allowed_equipment_class_ids = _scoped_equipment_class_ids(request)

    def scoped(queryset):
        return queryset.filter(
            Q(wed_routine_plan__isnull=False)
            | Q(wed_dart__isnull=False)
            | Q(obs_spare_id__equipment_class_id__in=allowed_equipment_class_ids)
        )

    survey_qs = scoped(
        models.SurveyReceiptsDetails.objects.filter(is_hod=True)
        .select_related(
            "wed_spares_id",
            "obs_spare_id",
            "wed_routine_plan",
            "wed_dart__dart_id__equipment_ship",
        )
        .exclude(is_sync=True)
        .order_by("-id")
    )
    demand_qs = scoped(
        models.DemandDetails.objects.filter(is_save=True)
        .select_related(
            "wed_spares_id",
            "obs_spare_id",
            "wed_routine_plan",
            "wed_dart__dart_id__equipment_ship",
        )
        .exclude(is_sync=True)
        .order_by("-id")
    )
    pts_qs = scoped(
        models.PTSDemandDetails.objects.filter(is_save=True)
        .select_related(
            "wed_spares_id",
            "obs_spare_id",
            "wed_routine_plan",
            "wed_dart__dart_id__equipment_ship",
        )
        .exclude(is_sync=True)
        .order_by("-id")
    )
    iif_qs = (
        models.WEDIIF.objects.filter(is_hod=True, is_delete=False)
        .select_related("spare_id", "spare_id__equipment_class", "user_id")
        .exclude(is_sync=True)
        .order_by("-id")
    )

    department_id = request.user.department_id
    if department_id:
        survey_qs = survey_qs.filter(user_id__department_id=department_id)
        demand_qs = demand_qs.filter(user_id__department_id=department_id)
        pts_qs = pts_qs.filter(user_id__department_id=department_id)
        iif_qs = iif_qs.filter(user_id__department_id=department_id)

    survey_entries = list(survey_qs)
    demand_entries = list(demand_qs)
    pts_entries = list(pts_qs)
    iif_entries = list(iif_qs)

    for entry in survey_entries:
        entry.item_serial_no = "—"
        if entry.spare_cart_name == "Survey":
            survey_form = (
                models.SurveyFormsDetails.objects.filter(survey_rec_id=entry)
                .order_by("-id")
                .first()
            )
            if survey_form:
                serial_nos = [
                    value
                    for value in models.SurveyFormsItems.objects.filter(
                        survey_details_id=survey_form
                    ).values_list("item_serial_no", flat=True)
                    if value
                ]
                entry.item_serial_no = ", ".join(serial_nos) if serial_nos else "—"

    for entry in demand_entries:
        entry.item_serial_no = "—"
    for entry in pts_entries:
        entry.item_serial_no = "—"

    for entry in iif_entries:
        entry.spare_cart_name = "IIF"
        entry.item_serial_no = "—"
        entry.dart_number = "—"
        entry.routine_description = "—"
        entry.equipment_nomenclature = (
            entry.spare_id.equipment_class.name
            if entry.spare_id and entry.spare_id.equipment_class
            else "—"
        )
        entry.quantity_required = (
            entry.spare_id.quantity_authorised
            if entry.spare_id and entry.spare_id.quantity_authorised
            else "—"
        )

    survey_entries = [_annotate_wlms_cart_entry(entry) for entry in survey_entries]
    demand_entries = [_annotate_wlms_cart_entry(entry) for entry in demand_entries]
    pts_entries = [_annotate_wlms_cart_entry(entry) for entry in pts_entries]

    def serialize(entry, serializer_class):
        data = serializer_class(entry).data
        for extra_field in (
            "dart_number",
            "equipment_name",
            "routine_description",
            "equipment_nomenclature",
            "quantity_required",
            "item_serial_no",
            "spare_cart_name",
        ):
            data[extra_field] = getattr(entry, extra_field, "—")
        return data

    all_entries = (
        [
            serialize(entry, serializers.SurveyReceiptsDetailsSerializer)
            for entry in survey_entries
        ]
        + [
            serialize(entry, serializers.DemandDetailsSerializer)
            for entry in demand_entries
        ]
        + [
            serialize(entry, serializers.PTSDemandDetailsSerializer)
            for entry in pts_entries
        ]
        + [serialize(entry, serializers.WEDIIFSerializer) for entry in iif_entries]
    )

    return Response({"pts_entries": all_entries})
