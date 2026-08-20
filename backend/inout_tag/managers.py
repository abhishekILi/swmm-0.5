"""Managers and querysets for the inout_tag app."""

from django.db import models
from django.db.models import Q


class TagOutQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related(
            "tagout_equipment_name",
            "user_profile",
            "approved_by",
        ).prefetch_related("departments_affected")

    def search(self, query):
        if not query:
            return self
        return self.filter(
            Q(tagout_number__icontains=query)
            | Q(name_of_component__icontains=query)
            | Q(name_of_subsystem__icontains=query)
            | Q(tagout_equipment_name__nomenclature__icontains=query)
        )

    def filter_view(
        self,
        *,
        approval_status=None,
        department=None,
        equipment=None,
        from_date=None,
        to_date=None,
    ):
        queryset = self
        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)
        if department:
            queryset = queryset.filter(departments_affected=department)
        if equipment:
            queryset = queryset.filter(tagout_equipment_name=equipment)
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
        return queryset.distinct()

    def pending(self):
        return self.filter(approval_status="in_progress")

    def approved(self):
        return self.filter(approval_status="approved")

    def rejected(self):
        return self.filter(approval_status="rejected")

    def awaiting_tagin(self):
        return self.approved().filter(tagin__isnull=True)


class TagInQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("tagout")


class TagInApprovalQuerySet(models.QuerySet):
    def with_related(self):
        return self.select_related("tagin", "department", "approved_by")

    def pending(self):
        return self.filter(approval_status="pending")


__all__ = ["TagOutQuerySet", "TagInQuerySet", "TagInApprovalQuerySet"]
