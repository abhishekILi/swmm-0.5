from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from master.models import Department, Ship
from users.models import CustomUserProfile

from .constants import (
    PlannerCategory,
    PlannerLane,
    PlannerPriority,
    PlannerStatus,
    get_lane_for_department,
)
from .managers import EventQuerySet, PlannerActivityQuerySet


class Event(models.Model):
    objects = EventQuerySet.as_manager()

    CATEGORY_CHOICES = (
        ("defect", "Defect"),
        ("routine", "Routine"),
        ("trial", "Trial"),
        ("audit", "Audit"),
        ("others", "Others"),
    )
    user = models.ForeignKey(
        CustomUserProfile, on_delete=models.PROTECT, blank=True, null=True
    )
    title = models.CharField(max_length=200)
    start_date = models.DateField(db_column="date")
    end_date = models.DateField(null=True, blank=True, db_column="EndDate")
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    document = models.FileField(upload_to="event_docs/", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or ""


class PlannerActivity(models.Model):
    objects = PlannerActivityQuerySet.as_manager()

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="planner_activities",
    )
    ship = models.ForeignKey(
        Ship,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="planner_activities",
    )

    lane = models.CharField(
        max_length=20,
        choices=PlannerLane.choices,
        default=PlannerLane.ENGINEERING,
    )
    category = models.CharField(
        max_length=20,
        choices=PlannerCategory.choices,
        default=PlannerCategory.OTHERS,
    )
    status = models.CharField(
        max_length=20,
        choices=PlannerStatus.choices,
        default=PlannerStatus.SCHEDULED,
    )
    priority = models.CharField(
        max_length=20,
        choices=PlannerPriority.choices,
        blank=True,
        null=True,
    )
    progress = models.PositiveSmallIntegerField(default=0)

    active = models.BooleanField(default=False)
    delayed = models.BooleanField(default=False)
    conflict = models.BooleanField(default=False)
    selected = models.BooleanField(default=False)
    isolation = models.BooleanField(default=False)

    equipment = models.CharField(max_length=255, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="created_planner_activities",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time", "id"]

    def clean(self):
        super().clean()
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError(
                {
                    "end_time": "End time must be after start time for same-day planner activities."
                }
            )

    def save(self, *args, **kwargs):
        previous_scope = None
        if self.pk:
            previous_scope = (
                PlannerActivity.objects.filter(pk=self.pk)
                .values_list("date", "lane")
                .first()
            )

        if not self.lane and self.department_id:
            self.lane = get_lane_for_department(getattr(self.department, "name", None))

        self.full_clean()
        super().save(*args, **kwargs)

        from .services import refresh_planner_state_for_scope

        refresh_planner_state_for_scope(self.date, self.lane)
        if previous_scope and previous_scope != (self.date, self.lane):
            refresh_planner_state_for_scope(*previous_scope)

    def __str__(self):
        return self.title or ""
