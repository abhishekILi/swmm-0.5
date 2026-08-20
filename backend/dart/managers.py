"""Managers and querysets for the dart app."""

from django.db import models
from django.db.models import Avg, Sum


class InitiateDartQuerySet(models.QuerySet):
    def open(self):
        return self.filter(is_closed=False)

    def closed(self):
        return self.filter(is_closed=True)

    def for_department(self, department):
        return self.filter(department_id=department)

    def operational(self):
        return self.filter(maintenance_period="OPERATIONAL")

    def refit(self):
        return self.filter(maintenance_period="REFIT")

    def non_ops(self):
        return self.filter(severity_code__severity_name__icontains="Non-Ops")

    def trial_required(self):
        return self.filter(trial_required=True)

    def spares_required(self):
        return self.filter(sapres_required=True)

    def ra_initiated(self):
        return self.filter(is_ra_initiate=True)

    def with_non_empty_description(self):
        return self.exclude(defective_discriptions=None)

    def for_ids(self, ids):
        return self.filter(id__in=ids)

    def pending_cmms_sync(self):
        return self.filter(cmms_sync_status=False)

    def with_priority_relations(self):
        return self.select_related("equipment_ems", "severity_code")

    def with_history_relations(self):
        return self.select_related(
            "equipment_ship__equipment",
            "equipment_ship__sub_department_f_key",
            "remark_code",
            "department_id",
        ).prefetch_related("ra_dl_entries")

    def for_equipment_ship(self, equipment):
        return self.filter(equipment_ship=equipment)

    def for_equipment_ems(self, equipment):
        return self.filter(equipment_ems=equipment)

    def distinct_equipment_ship_count(self):
        return self.values("equipment_ship").distinct().count()

    def repeated_failures_count(self):
        return (
            self.values("equipment_ship")
            .annotate(defect_count=models.Count("id"))
            .filter(defect_count__gt=1)
            .count()
        )

    def mark_ra_initiated(self):
        return self.update(is_ra_initiate=True)

    def mark_ra_draft(self):
        return self.update(is_ra_draft=True)

    def mark_dl_draft(self):
        return self.update(is_dl_draft=True)


class CompleteDefectDartQuerySet(models.QuerySet):
    def with_dart_details(self):
        return self.select_related("dart_details")

    def for_dart(self, dart):
        return self.filter(dart_details=dart)

    def ordered_by_rectified_date(self):
        return self.order_by("-rectified_date")

    def for_equipment_ship(self, equipment):
        return self.filter(dart_details__equipment_ship=equipment)

    def for_equipment_ems(self, equipment):
        return self.filter(dart_details__equipment_ems=equipment)

    def average_days_delay(self):
        return self.aggregate(value=Avg("days_delay"))["value"] or 0


class CompletedRoutineQuerySet(models.QuerySet):
    def ordered_by_completion(self):
        return self.order_by("-date_of_completion")

    def total_hours(self):
        return self.aggregate(value=Sum("hours"))["value"] or 0

    def total_manpower(self):
        return self.aggregate(value=Sum("total_manpower"))["value"] or 0


class TempDartSpareQuerySet(models.QuerySet):
    def active_items(self):
        return self.filter(is_delete=False)

    def for_equipment(self, equipment_id):
        return self.filter(equipment_id=equipment_id)
