from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer

from dart.models import InitiateDart
from sfd.models import ShipEquipment

from . import models


class MOItemEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MOItemEquipment
        fields = (
            "id",
            "itemcode",
            "eask_item_code",
            "eask_type",
            "qty_constituent",
            "qty_range_scale",
            "eask_book_ref",
            "datetime_approved",
            "approved_by",
            "datetime_closed",
            "closed_by",
            "trigger_remarks",
            "user_remarks",
            "eask_serial",
        )


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Item
        fields = (
            "item_code",
            "section_head",
            "item_desc",
            "country_code",
            "item_deno",
            "months_shelf_life",
            "crp_category",
            "ved_category",
            "abc_category",
            "datetime_approved",
            "approved_by",
            "review_sub_section_code",
            "incat_yn",
        )


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Vendor
        fields = (
            "vendor_code",
            "name",
            "vendor_class",
            "manufacturer_priority",
            "addressee",
            "address_line1",
            "address_line2",
            "address_line3",
            "city",
            "state",
            "pin_code",
            "country_code",
            "datetime_approved",
            "approved_by",
            "date_banned_upto",
            "section_head",
            "kompass_control_no",
            "remarks",
            "station_code",
            "ncage",
            "gem_seller_id",
            "business_id",
            "def_proc_id",
            "msme_registration_no",
            "gst_no",
            "pan",
        )


class MoMappingTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MoMappingTable
        fields = ("id", "ilms_spare_id", "vendor_id", "equipment")


class MOPlannedSparesDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.MOPlannedSparesDescription
        fields = ("id", "item_id", "routine_description_id", "is_deleted")


class PlannedMOSpareListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PlannedMOSpareList
        fields = (
            "id",
            "pattern_number",
            "planned_spares_description",
            "quantity_required",
            "is_deleted",
        )


class SurveyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SurveyDetails
        fields = (
            "id",
            "custom_user",
            "vendor_id",
            "ilms_spare_id",
            "obs_spare_id",
            "mo_routine_plan",
            "mo_dart",
            "demand_number",
            "in_progress_status",
            "is_survey",
            "is_sync",
            "is_hod",
            "is_hod_approval",
            "mo_survey_status",
        )


class PTSDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PTSDetails
        fields = (
            "id",
            "custom_user",
            "vendor_id",
            "ilms_spare_id",
            "obs_spare_id",
            "mo_routine_plan",
            "mo_dart",
            "in_progress_status",
            "pts_number",
            "is_pts",
            "is_sync",
            "is_hod",
            "is_hod_approval",
            "mo_pts_status",
        )


@extend_schema_serializer(component_name="IlmsDemandDetails")
class DemandDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DemandDetails
        fields = (
            "id",
            "custom_user",
            "vendor_id",
            "ilms_spare_id",
            "obs_spare_id",
            "mo_routine_plan",
            "mo_dart",
            "in_progress_status",
            "demand_number",
            "is_demand",
            "is_sync",
            "is_hod",
            "is_hod_approval",
            "mo_status",
        )


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Customer
        fields = (
            "customer_code",
            "name",
            "customer_type",
            "mother_depot",
            "addressee",
            "address_line1",
            "address_line2",
            "address_line3",
            "city",
            "state",
            "pin_code",
            "allowance_annual_rs",
            "date_introduced",
            "date_closed",
            "remarks",
            "admin_authority",
            "station_code",
            "added_by",
            "closed_by",
        )


class ItemLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ItemLine
        fields = (
            "item_code",
            "station_code",
            "sh_no",
            "qty_war_reserve",
            "qty_msl",
            "qty_usl",
            "qty_acl",
            "days_lt_proc",
            "datetime_added",
            "datetime_closed",
            "item_line_serial",
        )
        read_only_fields = ("item_line_serial",)


class CustomerEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerEquipment
        fields = (
            "id",
            "customer",
            "equipment",
            "qty_ship_fit",
            "qty_present",
            "date_quantity_present",
            "added_by",
            "datetime_added",
            "approved_by",
            "datetime_approved",
            "closed_by",
            "datetime_closed",
        )


class CustomerEquipmentLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerEquipmentLine
        fields = (
            "customer_eqpt_line_ser",
            "customer",
            "equipment",
            "eqpt_serial_number",
            "position_specific_yn",
            "fitment_port_stbd",
            "rotation_rl",
            "eqpt_nomenclature",
            "generic_code",
            "eqpt_type",
            "manufacturer_name",
            "supplier_name",
            "parent_eqpt",
            "location_code",
            "location_onboard",
            "location_fit",
            "remarks",
            "added_by",
            "datetime_added",
            "closed_by",
            "datetime_closed",
        )
        read_only_fields = ("customer_eqpt_line_ser",)


class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Price
        fields = (
            "id",
            "item",
            "price_type",
            "price_date",
            "price_ref",
            "price_cc",
            "currency_code",
            "vendor",
            "qty",
            "datetime_approved",
            "approved_by",
            "station_code",
        )


class ItemIssuedSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ItemIssued
        fields = (
            "id",
            "customer",
            "demand_no",
            "item",
            "sh_no",
            "qty",
            "price_rs",
            "datetime_obd",
            "issue_datetime",
            "issued_by",
            "station_code",
            "issued_type",
        )


class IssuedDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.IssuedDetails
        fields = (
            "id",
            "abc_ved_year",
            "station_code",
            "item",
            "no_of_issues",
            "qty_issued",
            "issued_cost",
        )


class ItemVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ItemVendor
        fields = (
            "item",
            "vendor",
            "active_yn",
            "rating",
            "certification_no",
            "certification_type",
            "pac_ref",
            "date_pac",
            "datetime_approved",
            "approved_by",
            "remarks",
            "datetime_till",
            "closed_by",
            "station_code",
            "datetime_closed",
            "item_vendor_serial_no",
        )
        read_only_fields = ("item_vendor_serial_no",)


class ItemExtraSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ItemExtra
        fields = (
            "item_code",
            "item_desc",
            "equipment_name",
            "category",
            "critical",
            "item_deno",
            "ved_category",
            "abc_category",
            "crp_category",
            "datetime_approved",
            "approved_by",
            "remarks",
            "image",
        )


class VendorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.VendorList
        fields = (
            "id",
            "vendorcode",
            "name",
            "class_field",
            "manufacturerpriority",
            "addressee",
            "addressline1",
            "addressline2",
            "addressline3",
            "city",
            "state",
            "pincode",
            "countrycode",
            "datetimeapproved",
            "approvedby",
            "datebannedupto",
            "sectionhead",
            "kompasscontrolno",
            "remarks",
            "stationcode",
            "ncage",
            "gemsellerid",
            "businesstype",
            "defprocid",
            "msmeregistrationno",
            "gstno",
            "pan",
        )


class VendorPilSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.VendorPil
        fields = (
            "id",
            "eqpt_code",
            "eqpt_desc",
            "oem_name",
            "vendor_name",
            "vendor_code",
            "characteristics_name",
            "char_value",
            "item_code",
            "item_desc",
            "substitute_item_code",
            "substitute_type",
            "eask_type",
            "country_of_origin",
            "currency_code",
            "ved_cat",
            "make_model",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")


class DartMOSpareSerializer(serializers.ModelSerializer):
    equipment_id = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=ShipEquipment.objects.all(),
        required=False,
    )
    dart_id = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        queryset=InitiateDart.objects.all(),
        required=False,
    )
    quantity = serializers.IntegerField(max_value=9999, min_value=1)

    class Meta:
        model = models.DartMOSpare
        fields = (
            "id",
            "issue_obj",
            "equipment_id",
            "dart_id",
            "mo_spare",
            "pattern",
            "description",
            "quantity",
            "created_date",
            "modified_date",
            "is_delete",
        )
        read_only_fields = ("created_date", "modified_date")


class IIFSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.IIF
        fields = ("id", "spare_id", "is_sync", "sync_response", "is_delete")


class AddToWorkflowCartSerializer(serializers.Serializer):
    SOURCE_CHOICES = (
        ("planned", "Planned MO spare"),
        ("dart", "DART MO spare"),
        ("obs", "Onboard spare"),
    )

    source = serializers.ChoiceField(choices=SOURCE_CHOICES)
    source_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    class Meta:
        ref_name = "ILMSAddToWorkflowCart"


class AddToIIFCartSerializer(serializers.Serializer):
    spare_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    class Meta:
        ref_name = "ILMSAddToIIFCart"
