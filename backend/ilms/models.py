from django.db import models
from users.models import CustomUserProfile

from .managers import BaseManager


class MOItemEquipment(models.Model):
    objects = BaseManager()
    itemcode = models.CharField(max_length=50, null=True, blank=True)
    eask_item_code = models.CharField(max_length=50, null=True, blank=True)
    eask_type = models.CharField(max_length=50, null=True, blank=True)
    qty_constituent = models.IntegerField(null=True, blank=True)
    qty_range_scale = models.IntegerField(null=True, blank=True)
    eask_book_ref = models.CharField(max_length=100, null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=50, null=True, blank=True)
    datetime_closed = models.DateTimeField(null=True, blank=True)
    closed_by = models.CharField(max_length=50, null=True, blank=True)
    trigger_remarks = models.TextField(null=True, blank=True)
    user_remarks = models.TextField(null=True, blank=True)
    eask_serial = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.itemcode

    class Meta:
        db_table = "ILMS_moitemequipment"


class Item(models.Model):
    objects = BaseManager()
    item_code = models.CharField(max_length=50, primary_key=True)
    section_head = models.CharField(max_length=50, null=True, blank=True)
    item_desc = models.TextField(null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    item_deno = models.CharField(max_length=50, null=True, blank=True)
    months_shelf_life = models.IntegerField(null=True, blank=True)
    crp_category = models.CharField(max_length=10, null=True, blank=True)
    ved_category = models.CharField(max_length=10, null=True, blank=True)
    abc_category = models.CharField(max_length=10, null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=50, null=True, blank=True)
    review_sub_section_code = models.CharField(max_length=50, null=True, blank=True)
    incat_yn = models.BooleanField(default=False)

    def __str__(self):
        return self.item_code

    class Meta:
        db_table = "ILMS_item"


class Vendor(models.Model):
    objects = BaseManager()
    vendor_code = models.CharField(max_length=200, primary_key=True)
    name = models.CharField(max_length=200, null=True, blank=True)
    vendor_class = models.CharField(max_length=200, null=True, blank=True)
    manufacturer_priority = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    addressee = models.CharField(max_length=200, null=True, blank=True)
    address_line1 = models.CharField(max_length=555, null=True, blank=True)
    address_line2 = models.CharField(max_length=555, null=True, blank=True)
    address_line3 = models.CharField(max_length=555, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    state = models.CharField(max_length=200, null=True, blank=True)
    pin_code = models.CharField(max_length=200, null=True, blank=True)
    country_code = models.CharField(max_length=200, null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=200, null=True, blank=True)
    date_banned_upto = models.DateField(null=True, blank=True)
    section_head = models.CharField(max_length=200, null=True, blank=True)
    kompass_control_no = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    remarks = models.TextField(null=True, blank=True)
    station_code = models.CharField(max_length=200, null=True, blank=True)
    ncage = models.CharField(max_length=200, null=True, blank=True)
    gem_seller_id = models.CharField(max_length=200, null=True, blank=True)
    business_id = models.CharField(max_length=200, null=True, blank=True)
    def_proc_id = models.CharField(max_length=200, null=True, blank=True)
    msme_registration_no = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )
    gst_no = models.CharField(max_length=200, null=True, blank=True)
    pan = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return str(self.vendor_code)

    class Meta:
        db_table = "ILMS_vendor"


class MoMappingTable(models.Model):
    objects = BaseManager()
    ilms_spare_id = models.ForeignKey(
        Item, on_delete=models.CASCADE, blank=True, null=True
    )
    vendor_id = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, blank=True, null=True
    )
    equipment = models.ForeignKey(
        "sfd.ShipEquipment",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="ilms_mappings",
    )

    def __str__(self):
        return str(self.pk)

    class Meta:
        db_table = "ILMS_momappingtable"


class MOPlannedSparesDescription(models.Model):
    objects = BaseManager()
    item_id = models.ForeignKey(Item, on_delete=models.CASCADE, blank=True, null=True)
    routine_description_id = models.ForeignKey(
        "ems.RoutineDescription",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="ilms_planned_spares",
        db_column="routine_description_id",
    )
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        db_table = "ILMS_moplannedsparesdescription"


class PlannedMOSpareList(models.Model):
    objects = BaseManager()
    pattern_number = models.CharField(max_length=200, blank=True, default="")
    planned_spares_description = models.ForeignKey(
        MOPlannedSparesDescription,
        on_delete=models.CASCADE,
    )
    quantity_required = models.PositiveIntegerField(default=0)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pattern_number or self.pk)

    class Meta:
        db_table = "ILMS_plannedmosparelist"


class SurveyDetails(models.Model):
    objects = BaseManager()
    custom_user = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ilms_survey_details",
    )
    vendor_id = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, blank=True, null=True
    )
    ilms_spare_id = models.ForeignKey(
        Item, on_delete=models.CASCADE, blank=True, null=True
    )
    obs_spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_DEFAULT,
        default="",
        blank=True,
        null=True,
        related_name="obs_speare_survey",
    )
    mo_routine_plan = models.ForeignKey(
        MOPlannedSparesDescription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    mo_dart = models.ForeignKey(
        "DartMOSpare",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    demand_number = models.CharField(max_length=200, blank=True, default="")
    in_progress_status = models.CharField(max_length=200, blank=True, default="")
    is_survey = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_hod_approval = models.BooleanField(default=False)
    mo_survey_status = models.CharField(max_length=200, default="Pending")

    def __str__(self):
        return str(self.demand_number or self.pk)

    class Meta:
        db_table = "ILMS_surveydetails"


class PTSDetails(models.Model):
    objects = BaseManager()
    custom_user = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ilms_pts_details",
    )
    vendor_id = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, blank=True, null=True
    )
    ilms_spare_id = models.ForeignKey(
        Item, on_delete=models.CASCADE, blank=True, null=True
    )
    obs_spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_DEFAULT,
        default="",
        blank=True,
        null=True,
        related_name="obs_speare_PTS",
    )
    mo_routine_plan = models.ForeignKey(
        MOPlannedSparesDescription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    mo_dart = models.ForeignKey(
        "DartMOSpare",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    in_progress_status = models.CharField(max_length=200, blank=True, default="")
    pts_number = models.CharField(max_length=200, blank=True, default="")
    is_pts = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_hod_approval = models.BooleanField(default=False)
    mo_pts_status = models.CharField(max_length=200, default="Pending")

    def __str__(self):
        return str(self.in_progress_status or self.pk)

    class Meta:
        db_table = "ILMS_ptsdetails"


class DemandDetails(models.Model):
    objects = BaseManager()
    custom_user = models.ForeignKey(
        CustomUserProfile,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="ilms_demand_details",
    )
    vendor_id = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, blank=True, null=True
    )
    ilms_spare_id = models.ForeignKey(
        Item, on_delete=models.CASCADE, blank=True, null=True
    )
    obs_spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_DEFAULT,
        default="",
        blank=True,
        null=True,
        related_name="obs_speare_demand",
    )
    mo_routine_plan = models.ForeignKey(
        MOPlannedSparesDescription,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    mo_dart = models.ForeignKey(
        "DartMOSpare",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    in_progress_status = models.CharField(max_length=200, blank=True, default="")
    demand_number = models.CharField(max_length=200, blank=True, default="")
    is_demand = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    is_hod = models.BooleanField(default=False)
    is_hod_approval = models.BooleanField(default=False)
    mo_status = models.CharField(max_length=200, default="Pending")

    def __str__(self):
        return str(self.demand_number or self.pk)

    class Meta:
        db_table = "ILMS_modemanddetails"


class Customer(models.Model):
    objects = BaseManager()
    customer_code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    customer_type = models.CharField(max_length=50, null=True, blank=True)
    mother_depot = models.CharField(max_length=50, null=True, blank=True)
    addressee = models.CharField(max_length=100, null=True, blank=True)
    address_line1 = models.CharField(max_length=200, null=True, blank=True)
    address_line2 = models.CharField(max_length=200, null=True, blank=True)
    address_line3 = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    pin_code = models.CharField(max_length=10, null=True, blank=True)
    allowance_annual_rs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    date_introduced = models.DateField(null=True, blank=True)
    date_closed = models.DateField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    admin_authority = models.CharField(max_length=100, null=True, blank=True)
    station_code = models.CharField(max_length=50, null=True, blank=True)
    added_by = models.CharField(max_length=50, null=True, blank=True)
    closed_by = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return str(self.name or self.pk)

    class Meta:
        db_table = "ILMS_customer"


class ItemLine(models.Model):
    objects = BaseManager()
    item_code = models.ForeignKey(Item, on_delete=models.CASCADE)
    station_code = models.CharField(max_length=50, null=True, blank=True)
    sh_no = models.CharField(max_length=50, null=True, blank=True)
    qty_war_reserve = models.IntegerField(null=True, blank=True)
    qty_msl = models.IntegerField(null=True, blank=True)
    qty_usl = models.IntegerField(null=True, blank=True)
    qty_acl = models.IntegerField(null=True, blank=True)
    days_lt_proc = models.IntegerField(null=True, blank=True)
    datetime_added = models.DateTimeField(null=True, blank=True)
    datetime_closed = models.DateTimeField(null=True, blank=True)
    item_line_serial = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.station_code or self.pk)

    class Meta:
        db_table = "ILMS_itemline"


class CustomerEquipment(models.Model):
    objects = BaseManager()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    equipment = models.ForeignKey(
        "sfd.Equipment",
        on_delete=models.PROTECT,
        related_name="ilms_customer_equipment",
    )
    qty_ship_fit = models.IntegerField(null=True, blank=True)
    qty_present = models.IntegerField(null=True, blank=True)
    date_quantity_present = models.DateField(null=True, blank=True)
    added_by = models.CharField(max_length=50, null=True, blank=True)
    datetime_added = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=50, null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    closed_by = models.CharField(max_length=50, null=True, blank=True)
    datetime_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.added_by or self.pk)

    class Meta:
        db_table = "ILMS_customerequipment"


class CustomerEquipmentLine(models.Model):
    objects = BaseManager()
    customer_eqpt_line_ser = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    equipment = models.ForeignKey(
        "sfd.Equipment",
        on_delete=models.PROTECT,
        related_name="ilms_customer_equipment_lines",
    )
    eqpt_serial_number = models.CharField(max_length=100, null=True, blank=True)
    position_specific_yn = models.BooleanField(null=True, blank=True)
    fitment_port_stbd = models.CharField(max_length=50, null=True, blank=True)
    rotation_rl = models.CharField(max_length=50, null=True, blank=True)
    eqpt_nomenclature = models.CharField(max_length=100, null=True, blank=True)
    generic_code = models.CharField(max_length=50, null=True, blank=True)
    eqpt_type = models.CharField(max_length=50, null=True, blank=True)
    manufacturer_name = models.CharField(max_length=100, null=True, blank=True)
    supplier_name = models.CharField(max_length=100, null=True, blank=True)
    parent_eqpt = models.CharField(max_length=100, null=True, blank=True)
    location_code = models.CharField(max_length=100, null=True, blank=True)
    location_onboard = models.CharField(max_length=100, null=True, blank=True)
    location_fit = models.CharField(max_length=100, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    added_by = models.CharField(max_length=50, null=True, blank=True)
    datetime_added = models.DateTimeField(null=True, blank=True)
    closed_by = models.CharField(max_length=50, null=True, blank=True)
    datetime_closed = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.eqpt_serial_number or self.pk)

    class Meta:
        db_table = "ILMS_customerequipmentline"


class Price(models.Model):
    objects = BaseManager()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    price_type = models.CharField(max_length=50, null=True, blank=True)
    price_date = models.DateField(null=True, blank=True)
    price_ref = models.CharField(max_length=100, null=True, blank=True)
    price_cc = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency_code = models.CharField(max_length=10, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    qty = models.IntegerField(null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=50, null=True, blank=True)
    station_code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return str(self.price_type or self.pk)

    class Meta:
        db_table = "ILMS_price"


class ItemIssued(models.Model):
    objects = BaseManager()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    demand_no = models.CharField(max_length=50, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    sh_no = models.CharField(max_length=50, null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True)
    price_rs = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    datetime_obd = models.DateTimeField(null=True, blank=True)
    issue_datetime = models.DateTimeField(null=True, blank=True)
    issued_by = models.CharField(max_length=50, null=True, blank=True)
    station_code = models.CharField(max_length=50, null=True, blank=True)
    issued_type = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return str(self.demand_no or self.pk)

    class Meta:
        db_table = "ILMS_itemissued"


class IssuedDetails(models.Model):
    objects = BaseManager()
    abc_ved_year = models.CharField(max_length=10, null=True, blank=True)
    station_code = models.CharField(max_length=50, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    no_of_issues = models.IntegerField(null=True, blank=True)
    qty_issued = models.IntegerField(null=True, blank=True)
    issued_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    def __str__(self):
        return str(self.abc_ved_year or self.pk)

    class Meta:
        db_table = "ILMS_issueddetails"


class ItemVendor(models.Model):
    objects = BaseManager()
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    active_yn = models.BooleanField(null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True)
    certification_no = models.CharField(max_length=100, null=True, blank=True)
    certification_type = models.CharField(max_length=50, null=True, blank=True)
    pac_ref = models.CharField(max_length=50, null=True, blank=True)
    date_pac = models.DateField(null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=50, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    datetime_till = models.DateTimeField(null=True, blank=True)
    closed_by = models.CharField(max_length=50, null=True, blank=True)
    station_code = models.CharField(max_length=50, null=True, blank=True)
    datetime_closed = models.DateTimeField(null=True, blank=True)
    item_vendor_serial_no = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.certification_no or self.pk)

    class Meta:
        db_table = "ILMS_itemvendor"


class ItemExtra(models.Model):
    objects = BaseManager()
    PERMANENT = "PERMANENT"
    RETURNABLE = "RETURNABLE"
    CONSUMABLE = "CONSUMABLE"

    CATEGORY_CHOICES = [
        (PERMANENT, "PERMANENT"),
        (RETURNABLE, "RETURNABLE"),
        (CONSUMABLE, "CONSUMABLE"),
    ]

    item_code = models.CharField(max_length=50, primary_key=True)
    item_desc = models.TextField(null=True, blank=True)
    equipment_name = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=PERMANENT,
    )
    critical = models.BooleanField(default=False)
    item_deno = models.ForeignKey(
        "obs.Denomination", on_delete=models.PROTECT, blank=True, null=True
    )
    ved_category = models.CharField(max_length=10, null=True, blank=True)
    abc_category = models.CharField(max_length=10, null=True, blank=True)
    crp_category = models.CharField(max_length=10, null=True, blank=True)
    datetime_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=50, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    image = models.ImageField(
        upload_to="items/",
        default="default.png",
        null=True,
        blank=True,
    )

    def __str__(self):
        return str(self.item_code or self.pk)

    class Meta:
        db_table = "ILMS_item_extra"


class VendorList(models.Model):
    objects = BaseManager()
    vendorcode = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    class_field = models.CharField(max_length=255, blank=True, null=True)
    manufacturerpriority = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    addressee = models.CharField(max_length=255, blank=True, null=True)
    addressline1 = models.CharField(max_length=255, blank=True, null=True)
    addressline2 = models.CharField(max_length=255, blank=True, null=True)
    addressline3 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    pincode = models.CharField(max_length=255, blank=True, null=True)
    countrycode = models.CharField(max_length=255, blank=True, null=True)
    datetimeapproved = models.CharField(max_length=255, blank=True, null=True)
    approvedby = models.CharField(max_length=255, blank=True, null=True)
    datebannedupto = models.CharField(max_length=255, blank=True, null=True)
    sectionhead = models.CharField(max_length=255, blank=True, null=True)
    kompasscontrolno = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    stationcode = models.CharField(max_length=255, blank=True, null=True)
    ncage = models.CharField(max_length=255, blank=True, null=True)
    gemsellerid = models.CharField(max_length=255, blank=True, null=True)
    businesstype = models.CharField(max_length=255, blank=True, null=True)
    defprocid = models.CharField(max_length=255, blank=True, null=True)
    msmeregistrationno = models.CharField(max_length=255, blank=True, null=True)
    gstno = models.CharField(max_length=255, blank=True, null=True)
    pan = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "ILMS_vendor_list"


class VendorPil(models.Model):
    objects = BaseManager()
    eqpt_code = models.CharField(max_length=100, null=True, blank=True)
    eqpt_desc = models.CharField(max_length=255, null=True, blank=True)
    oem_name = models.CharField(max_length=255, null=True, blank=True)
    vendor_name = models.CharField(max_length=255, null=True, blank=True)
    vendor_code = models.CharField(max_length=255, null=True, blank=True)
    characteristics_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    char_value = models.CharField(max_length=255, null=True, blank=True)
    item_code = models.CharField(max_length=100, null=True, blank=True)
    item_desc = models.CharField(max_length=255, null=True, blank=True)
    substitute_item_code = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    substitute_type = models.CharField(max_length=100, null=True, blank=True)
    eask_type = models.CharField(max_length=100, null=True, blank=True)
    country_of_origin = models.CharField(max_length=100, null=True, blank=True)
    currency_code = models.CharField(max_length=10, null=True, blank=True)
    ved_cat = models.CharField(max_length=50, null=True, blank=True)
    make_model = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.eqpt_code} - {self.eqpt_desc}"

    class Meta:
        db_table = "ILMS_vendor_pil"


class DartMOSpare(models.Model):
    objects = BaseManager()
    issue_obj = models.ForeignKey(
        "obs.Issue",
        on_delete=models.SET_DEFAULT,
        default="",
        blank=True,
        null=True,
    )
    equipment_id = models.ForeignKey(
        "sfd.ShipEquipment",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="dart_mo_spares",
        db_column="equipment_id_id",
    )
    dart_id = models.ForeignKey(
        "dart.InitiateDart",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="mo_spares",
        db_column="dart_id_id",
    )
    mo_spare = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    pattern = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_date = models.DateField(auto_now_add=True, blank=True, null=True)
    modified_date = models.DateField(auto_now_add=True, blank=True, null=True)
    is_delete = models.BooleanField(default=False)

    def __str__(self):
        return str(self.description or self.pk)

    class Meta:
        db_table = "ILMS_dartmospare"


class IIF(models.Model):
    objects = BaseManager()
    spare_id = models.ForeignKey(
        "obs.Spares",
        on_delete=models.SET_DEFAULT,
        default="",
        blank=True,
        null=True,
    )
    is_sync = models.BooleanField(default=False)
    sync_response = models.BooleanField(default=False)
    is_delete = models.BooleanField(default=False)

    def __str__(self):
        return str(self.pk)

    class Meta:
        db_table = "ILMS_iif"
