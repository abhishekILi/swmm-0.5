from django.contrib import admin

from .models import (
    CompleteDefectDart,
    CompletedRoutine,
    CompletedRoutineSpare,
    DartSpare,
    DartSpareUsed,
    InitiateDart,
    InitiateRADL,
    RADLMaster,
    TempDartSpare,
)

# ─────────────────────────────────────────────────────────────
# Inline Admins
# ─────────────────────────────────────────────────────────────


class DartSpareUsedInline(admin.TabularInline):
    model = DartSpareUsed
    extra = 1
    fields = ("pattern_no", "description", "quantity")


class DartSpareInline(admin.TabularInline):
    model = DartSpare
    extra = 1
    fields = (
        "spare_id",
        "pattern",
        "inventory_type",
        "description",
        "quantity",
        "is_delete",
    )


class CompletedRoutineSpareInline(admin.TabularInline):
    model = CompletedRoutineSpare
    extra = 1
    fields = ("spare_name",)


class InitiateRADLInline(admin.TabularInline):
    model = InitiateRADL
    extra = 1
    fields = ("dl_no", "dl_type", "dl_key", "status", "is_active")
    raw_id_fields = ("initiate_dart",)


# ─────────────────────────────────────────────────────────────
# Model Admins
# ─────────────────────────────────────────────────────────────


@admin.register(InitiateDart)
class InitiateDartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "dart_number",
        "equipment_ship",
        "department_id",
        "dart_date",
        "is_closed",
        "is_guarantee_defect",
    )
    list_filter = (
        "department_id",
        "is_closed",
        "is_guarantee_defect",
        "trial_required",
        "sapres_required",
        "is_ra_initiate",
        "is_dl_initiate",
    )
    search_fields = (
        "dart_number",
        "dart_sr_number",
        "defective_discriptions",
        "defective_component",
    )
    raw_id_fields = (
        "equipment_ship",
        "equipment_ems",
        "symptom_code",
        "severity_code",
        "remark_code",
        "require_assistance_for_code",
        "refit_maintenance_period_f_key",
        "department_id",
    )
    readonly_fields = ("created_date",)
    inlines = [DartSpareInline, InitiateRADLInline]
    actions = ["mark_closed", "mark_open"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "dart_number",
                    "dart_sr_number",
                    "department_id",
                    "dart_date",
                    "rectification_date",
                    "created_date",
                    "is_closed",
                )
            },
        ),
        (
            "Equipment Details",
            {
                "fields": (
                    "equipment_ship",
                    "equipment_ems",
                    "defective_component",
                    "defective_discriptions",
                    "photograph",
                )
            },
        ),
        (
            "Classification & Categorization",
            {
                "fields": (
                    "symptom_code",
                    "severity_code",
                    "remark_code",
                    "require_assistance_for_code",
                    "refit_maintenance_period_f_key",
                    "maintenance_period",
                    "dart_occasion",
                )
            },
        ),
        (
            "Requirements",
            {
                "fields": (
                    "trial_required",
                    "universal_id_trial_required",
                    "sapres_required",
                )
            },
        ),
        (
            "Guarantee Defect Details",
            {
                "classes": ("collapse",),
                "fields": (
                    "is_guarantee_defect",
                    "guarantee_cause",
                    "guarantee_op_availability",
                    "guarantee_hot_work",
                    "guarantee_repairs",
                    "guarantee_completion_date",
                    "guarantee_repair_date",
                    "guarantee_place",
                ),
            },
        ),
        (
            "Status & Sync Info",
            {
                "fields": (
                    "ops_status",
                    "is_ra_initiate",
                    "is_dl_initiate",
                    "is_ra_draft",
                    "is_dl_draft",
                    "cmms_sync_status",
                    "cmms_sync_date",
                )
            },
        ),
    )

    @admin.action(description="Mark selected defects as Closed")
    def mark_closed(self, request, queryset):
        queryset.update(is_closed=True)

    @admin.action(description="Mark selected defects as Open")
    def mark_open(self, request, queryset):
        queryset.update(is_closed=False)


@admin.register(CompleteDefectDart)
class CompleteDefectDartAdmin(admin.ModelAdmin):
    list_display = ("id", "dart_no", "rectified_date", "days_delay")
    search_fields = ("dart_no", "defect_report", "lesson_learnt")
    list_filter = ("rectified_date", "days_delay")
    raw_id_fields = (
        "repair_agency_code",
        "diagnostic_code",
        "repair_code",
        "delay_code",
    )
    inlines = [DartSpareUsedInline]


@admin.register(DartSpareUsed)
class DartSpareUsedAdmin(admin.ModelAdmin):
    list_display = ("id", "complete_dart", "pattern_no", "description", "quantity")
    search_fields = ("pattern_no", "description")
    raw_id_fields = ("complete_dart",)


@admin.register(CompletedRoutine)
class CompletedRoutineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "routine",
        "old_dart_number",
        "new_dart_number",
        "date_of_completion",
        "hours",
        "total_manpower",
    )
    search_fields = ("routine", "old_dart_number", "new_dart_number", "carried_by")
    list_filter = ("date_of_completion", "isfuss_close", "not_applicable")
    readonly_fields = ("created_at",)
    inlines = [CompletedRoutineSpareInline]


@admin.register(RADLMaster)
class RADLMasterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ra_dl_name",
        "dockyard_name",
        "refit_type_name",
        "created_date",
    )
    search_fields = ("ra_dl_name", "dockyard_name", "refit_type_name")
    list_filter = ("created_date", "dockyard_name")
    inlines = [InitiateRADLInline]


@admin.register(DartSpare)
class DartSpareAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "dart",
        "spare_id",
        "pattern",
        "inventory_type",
        "quantity",
        "is_delete",
    )
    search_fields = ("pattern", "description", "dart__dart_number")
    list_filter = ("inventory_type", "is_delete")
    raw_id_fields = ("dart",)


@admin.register(TempDartSpare)
class TempDartSpareAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "spare_id",
        "pattern",
        "description",
        "quantity",
        "created_date",
        "is_delete",
    )
    search_fields = ("pattern", "description")
    list_filter = ("is_delete", "created_date")


@admin.register(CompletedRoutineSpare)
class CompletedRoutineSpareAdmin(admin.ModelAdmin):
    list_display = ("id", "completed_routine", "spare_name")
    search_fields = ("spare_name",)
    raw_id_fields = ("completed_routine",)


@admin.register(InitiateRADL)
class InitiateRADLAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "radl_master",
        "initiate_dart",
        "status",
        "dl_no",
        "dl_type",
        "is_active",
    )
    search_fields = ("dl_no", "dl_type", "dl_key", "initiate_dart__dart_number")
    list_filter = ("status", "is_active", "created_date")
    raw_id_fields = ("radl_master", "initiate_dart")
    readonly_fields = ("created_date", "updated_date")
