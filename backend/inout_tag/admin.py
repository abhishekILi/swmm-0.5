from django.contrib import admin

from .models import TagIn, TagInApproval, TagOut


@admin.register(TagOut)
class TagOutAdmin(admin.ModelAdmin):
    list_display = (
        "tagout_number",
        "date",
        "tagout_equipment_name",
        "approval_status",
    )
    list_filter = ("approval_status", "type", "date")
    search_fields = ("tagout_number", "tagout_equipment_name__nomenclature")
    readonly_fields = ("tagout_number",)


@admin.register(TagIn)
class TagInAdmin(admin.ModelAdmin):
    list_display = (
        "tagout",
        "tagin_date",
        "status",
        "approval_status",
    )
    list_filter = (
        "status",
        "approval_status",
        "tagin_date",
    )
    search_fields = ("tagout__tagout_number",)


@admin.register(TagInApproval)
class TagInApprovalAdmin(admin.ModelAdmin):
    list_display = (
        "tagin",
        "department",
        "approval_status",
        "approved_by",
        "approved_on",
    )
    list_filter = (
        "approval_status",
        "department",
        "approved_on",
    )
    search_fields = (
        "tagin__tagout__tagout_number",
        "department__name",
    )
