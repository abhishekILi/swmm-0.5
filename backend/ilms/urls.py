from django.urls import path

from . import views

app_name = "ilms"

items = views.ItemViewSet.as_view({"get": "list", "post": "create"})
item_dashboard = views.ItemViewSet.as_view({"get": "dashboard"})
item_search_list = views.ItemViewSet.as_view({"get": "search_list"})
item_context = views.ItemViewSet.as_view({"get": "context"})
item_search_enriched = views.ItemViewSet.as_view({"get": "search_enriched"})
item_export_excel = views.ItemViewSet.as_view({"get": "export_excel"})
item_download_template = views.ItemViewSet.as_view({"get": "download_template"})
item_import_excel = views.ItemViewSet.as_view({"post": "import_excel"})
vendors = views.VendorViewSet.as_view({"get": "list", "post": "create"})
vendor_search_list = views.VendorViewSet.as_view({"get": "search_list"})
vendor_search_table = views.VendorViewSet.as_view({"get": "search_table"})
vendor_export_excel = views.VendorViewSet.as_view({"get": "export_excel"})
vendor_download_template = views.VendorViewSet.as_view({"get": "download_template"})
vendor_import_excel = views.VendorViewSet.as_view({"post": "import_excel"})
planned_spares_by_routine = views.PlannedMOSpareListViewSet.as_view(
    {"get": "by_routine"}
)
routines_by_department = views.PlannedMOSpareListViewSet.as_view(
    {"get": "routines_by_department"}
)

surveys = views.SurveyDetailsViewSet.as_view({"get": "list", "post": "create"})
survey_pending_list = views.SurveyDetailsViewSet.as_view({"get": "pending_list"})
survey_add_to_cart = views.SurveyDetailsViewSet.as_view({"post": "add_to_cart"})
survey_send_for_approval = views.SurveyDetailsViewSet.as_view(
    {"post": "send_for_approval"}
)
survey_inbox = views.SurveyDetailsViewSet.as_view({"get": "inbox"})
survey_outbox = views.SurveyDetailsViewSet.as_view({"get": "outbox"})
survey_bulk_send = views.SurveyDetailsViewSet.as_view(
    {"post": "bulk_send_for_approval"}
)
survey_approve = views.SurveyDetailsViewSet.as_view({"post": "approve"})
survey_bulk_approve = views.SurveyDetailsViewSet.as_view({"post": "bulk_approve"})
survey_complete = views.SurveyDetailsViewSet.as_view({"post": "complete"})
survey_mark_synced = views.SurveyDetailsViewSet.as_view({"post": "mark_synced"})
survey_export_excel = views.SurveyDetailsViewSet.as_view({"get": "export_excel"})
survey_import_excel = views.SurveyDetailsViewSet.as_view({"post": "import_excel"})

pts = views.PTSDetailsViewSet.as_view({"get": "list", "post": "create"})
pts_pending_list = views.PTSDetailsViewSet.as_view({"get": "pending_list"})
pts_add_to_cart = views.PTSDetailsViewSet.as_view({"post": "add_to_cart"})
pts_send_for_approval = views.PTSDetailsViewSet.as_view({"post": "send_for_approval"})
pts_inbox = views.PTSDetailsViewSet.as_view({"get": "inbox"})
pts_outbox = views.PTSDetailsViewSet.as_view({"get": "outbox"})
pts_bulk_send = views.PTSDetailsViewSet.as_view({"post": "bulk_send_for_approval"})
pts_approve = views.PTSDetailsViewSet.as_view({"post": "approve"})
pts_bulk_approve = views.PTSDetailsViewSet.as_view({"post": "bulk_approve"})
pts_complete = views.PTSDetailsViewSet.as_view({"post": "complete"})
pts_mark_synced = views.PTSDetailsViewSet.as_view({"post": "mark_synced"})

demands = views.DemandDetailsViewSet.as_view({"get": "list", "post": "create"})
demand_pending_list = views.DemandDetailsViewSet.as_view({"get": "pending_list"})
demand_bulk_send = views.DemandDetailsViewSet.as_view(
    {"post": "bulk_send_for_approval"}
)
demand_add_to_cart = views.DemandDetailsViewSet.as_view({"post": "add_to_cart"})
demand_send_for_approval = views.DemandDetailsViewSet.as_view(
    {"post": "send_for_approval"}
)
demand_approve = views.DemandDetailsViewSet.as_view({"post": "approve"})
demand_bulk_approve = views.DemandDetailsViewSet.as_view({"post": "bulk_approve"})
demand_outbox = views.DemandDetailsViewSet.as_view({"get": "outbox"})
demand_complete = views.DemandDetailsViewSet.as_view({"post": "complete"})
demand_mark_synced = views.DemandDetailsViewSet.as_view({"post": "mark_synced"})
demand_generate_number = views.DemandDetailsViewSet.as_view({"post": "generate_number"})
demand_receive_queue = views.DemandDetailsViewSet.as_view({"get": "receive_queue"})
demand_merged_receive_list = views.DemandDetailsViewSet.as_view(
    {"get": "merged_receive_list"}
)
demand_consolidation = views.DemandDetailsViewSet.as_view({"get": "consolidation"})

iif = views.IIFViewSet.as_view({"get": "list", "post": "create"})
iif_add_items = views.IIFViewSet.as_view({"post": "add_items"})
iif_mark_synced = views.IIFViewSet.as_view({"post": "mark_synced"})
mo_item_equipment = views.MOItemEquipmentViewSet.as_view({"get": "list"})

wed_item_search = views.WedInventoryViewSet.as_view({"get": "item_search"})
wed_survey_list = views.WedInventoryViewSet.as_view({"get": "survey_list"})
wed_demand_list = views.WedInventoryViewSet.as_view({"get": "demand_list"})
wed_receive_list = views.WedInventoryViewSet.as_view({"get": "receive_list"})
wed_pts_list = views.WedInventoryViewSet.as_view({"get": "pts_list"})
obs_generate_demand_list = views.WedInventoryViewSet.as_view(
    {"get": "generate_demand_list"}
)
obs_save_demand = views.WedInventoryViewSet.as_view({"post": "save_demand"})
obs_demanded_spares = views.WedInventoryViewSet.as_view({"get": "demanded_spares"})

mo_mapping_table = views.MoMappingTableViewSet.as_view(
    {"get": "list", "post": "create"}
)
mo_mapping_table_detail = views.MoMappingTableViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
mo_planned_spares_description = views.MOPlannedSparesDescriptionViewSet.as_view(
    {"get": "list", "post": "create"}
)
customers = views.CustomerViewSet.as_view({"get": "list", "post": "create"})
item_lines = views.ItemLineViewSet.as_view({"get": "list", "post": "create"})
customer_equipment = views.CustomerEquipmentViewSet.as_view(
    {"get": "list", "post": "create"}
)
customer_equipment_line = views.CustomerEquipmentLineViewSet.as_view(
    {"get": "list", "post": "create"}
)
prices = views.PriceViewSet.as_view({"get": "list", "post": "create"})
items_issued = views.ItemIssuedViewSet.as_view({"get": "list", "post": "create"})
issued_details = views.IssuedDetailsViewSet.as_view({"get": "list", "post": "create"})
item_vendors = views.ItemVendorViewSet.as_view({"get": "list", "post": "create"})
item_extras = views.ItemExtraViewSet.as_view({"get": "list", "post": "create"})
vendor_lists = views.VendorListViewSet.as_view({"get": "list", "post": "create"})
vendor_pils = views.VendorPilViewSet.as_view({"get": "list", "post": "create"})
dart_mo_spares = views.DartMOSpareViewSet.as_view({"get": "list", "post": "create"})

urlpatterns = [
    path("", item_dashboard, name="home"),
    path("vendor_search/", vendor_search_table, name="vendor_search"),
    path("item_search/", item_search_enriched, name="item_search"),
    path(
        "generate_demand_list/", obs_generate_demand_list, name="generate_demand_list"
    ),
    path("save_demand/", obs_save_demand, name="save_demand"),
    path("demanded_spare/", obs_demanded_spares, name="demanded_spare"),
    path("transaction/create_cart/", iif, name="create_cart"),
    path("transaction/add-to-cart/", survey_add_to_cart, name="add_to_cart"),
    path("transaction/demand_action/", demand_add_to_cart, name="demand_action"),
    path("transaction/issue_auth/", iif, name="issue_auth"),
    path("transaction/ars_issue/", iif, name="ars_issue"),
    path(
        "transaction/demand_consolidation/",
        demand_consolidation,
        name="demand_consolidation",
    ),
    path("transaction/accounting/", iif, name="accounting"),
    path("transaction/return/", iif, name="return"),
    path("transaction/gate_pass/", iif, name="gate_pass"),
    path("transaction/consumption/", iif, name="consumption"),
    path("transaction/enac_request/", iif, name="enac_request"),
    path("transaction/survey/", surveys, name="survey"),
    path("transaction/stock_transfer/", iif, name="stock_transfer"),
    path("transaction/obs_master/", iif, name="obs_master"),
    path("mis/mo_demand_status/", demands, name="mo_demand_status"),
    path("mis/pending_hq_demand/", demands, name="pending_hq_demand"),
    path("action/inbox/", views.ilms_combined_inbox, name="inbox"),
    path("action/outbox/", survey_outbox, name="outbox"),
    path(
        "action/generate_condition_certificate/",
        iif,
        name="generate_condition_certificate",
    ),
    path("dashboard/", item_dashboard, name="dashboard"),
    path("master/", mo_mapping_table, name="master"),
    path("iifhistory/", iif, name="iifhistory"),
    path("iifcart/", iif, name="iifcart"),
    path("add-to-iif-cart/", iif_add_items, name="add_to_iif_cart"),
    path("mo_survey_list/", survey_pending_list, name="mo_survey_list"),
    path("mo_demand_list/", demand_pending_list, name="mo_demandlist"),
    path("mo_receive_list/", demand_merged_receive_list, name="mo_receivelist"),
    path("mo_pts_list/", pts_pending_list, name="mo_pts_list"),
    path("ptsraised_surveypending/", pts, name="ptsraised_surveypending"),
    path("mo_surveydetail/", surveys, name="mo_surveydetail"),
    path("mo_ptsdetail/", pts, name="mo_ptsdetail"),
    path("mo_demanddetail/", demands, name="mo_demanddetail"),
    path("mo_receivedetail/", demand_receive_queue, name="mo_receivedetail"),
    path("wed_item_search/", wed_item_search, name="wed_item_search"),
    path("wed_vendor_search/", vendor_search_table, name="wed_vendor_search"),
    path("wed_survey_list/", wed_survey_list, name="wed_surveylist"),
    path("wed_demand_list/", wed_demand_list, name="wed_demandlist"),
    path("wed_receive_list/", wed_receive_list, name="wed_receivelist"),
    path("wed_pts_list/", wed_pts_list, name="wed_ptslist"),
    path("ilmsdashboard/", item_dashboard, name="ilmsdashboard"),
    path("ilms_master/", mo_mapping_table, name="ilms_master"),
    path("vendor-search-list/", vendor_search_list, name="vendor_search_list"),
    path("item-search-list/", item_search_list, name="item_search_list"),
    path(
        "demand_data_send_ilms/",
        views.demand_data_send_ilms,
        name="demand_data_send_ilms",
    ),
    path("pts_data_send_ilms/", views.pts_data_send_ilms, name="pts_data_send_ilms"),
    path("ilmshistory/", items, name="ilmshistory"),
    path("pts_send_hod_approval/", pts_bulk_send, name="pts_send_hod_approval"),
    path(
        "demand_send_hod_approval/", demand_bulk_send, name="demand_send_hod_approval"
    ),
    path("approve-pts/", pts_bulk_approve, name="approve_pts"),
    path(
        "get_routine_by_equipment/",
        routines_by_department,
        name="get_routine_by_equipment",
    ),
    path(
        "survey_send_hod_approval/", survey_bulk_send, name="survey_send_hod_approval"
    ),
    path(
        "planned-mo-spares/by-routine/",
        planned_spares_by_routine,
        name="planned_mo_spares_by_routine",
    ),
    # Approval-workflow actions that already existed in views.py but were never
    # routed for Survey/PTS/Demand (only bulk-send/some bulk-approve were wired).
    path(
        "survey/<int:pk>/send-for-approval/",
        survey_send_for_approval,
        name="survey_send_for_approval",
    ),
    path("survey/<int:pk>/approve/", survey_approve, name="survey_approve"),
    path("survey/bulk-approve/", survey_bulk_approve, name="survey_bulk_approve"),
    path("survey/<int:pk>/complete/", survey_complete, name="survey_complete"),
    path(
        "survey/<int:pk>/mark-synced/",
        survey_mark_synced,
        name="survey_mark_synced",
    ),
    path("survey/export-excel/", survey_export_excel, name="survey_export_excel"),
    path("survey/import-excel/", survey_import_excel, name="survey_import_excel"),
    path("pts/add-to-cart/", pts_add_to_cart, name="pts_add_to_cart"),
    path(
        "pts/<int:pk>/send-for-approval/",
        pts_send_for_approval,
        name="pts_send_for_approval",
    ),
    path("pts/inbox/", pts_inbox, name="pts_inbox"),
    path("pts/outbox/", pts_outbox, name="pts_outbox"),
    path("pts/<int:pk>/approve/", pts_approve, name="pts_approve"),
    path("pts/<int:pk>/complete/", pts_complete, name="pts_complete"),
    path("pts/<int:pk>/mark-synced/", pts_mark_synced, name="pts_mark_synced"),
    path(
        "demand/<int:pk>/send-for-approval/",
        demand_send_for_approval,
        name="demand_send_for_approval",
    ),
    path("demand/<int:pk>/approve/", demand_approve, name="demand_approve"),
    path("demand/bulk-approve/", demand_bulk_approve, name="demand_bulk_approve"),
    path("demand/outbox/", demand_outbox, name="demand_outbox"),
    path("demand/<int:pk>/complete/", demand_complete, name="demand_complete"),
    path(
        "demand/<int:pk>/mark-synced/",
        demand_mark_synced,
        name="demand_mark_synced",
    ),
    path(
        "demand/<int:pk>/generate-number/",
        demand_generate_number,
        name="demand_generate_number",
    ),
    path("item/<int:pk>/context/", item_context, name="item_context"),
    path("item/export-excel/", item_export_excel, name="item_export_excel"),
    path(
        "item/download-template/",
        item_download_template,
        name="item_download_template",
    ),
    path("item/import-excel/", item_import_excel, name="item_import_excel"),
    path("vendor/export-excel/", vendor_export_excel, name="vendor_export_excel"),
    path(
        "vendor/download-template/",
        vendor_download_template,
        name="vendor_download_template",
    ),
    path("vendor/import-excel/", vendor_import_excel, name="vendor_import_excel"),
    path("iif/<int:pk>/mark-synced/", iif_mark_synced, name="iif_mark_synced"),
    # Full CRUD for viewsets that existed in views.py with zero routes at all.
    path("mo-item-equipment/", mo_item_equipment, name="mo_item_equipment"),
    path("mo-mapping-table/", mo_mapping_table, name="mo_mapping_table"),
    path(
        "mo-mapping-table/<int:pk>/",
        mo_mapping_table_detail,
        name="mo_mapping_table_detail",
    ),
    path(
        "mo-planned-spares-description/",
        mo_planned_spares_description,
        name="mo_planned_spares_description",
    ),
    path("customers/", customers, name="customers"),
    path("item-lines/", item_lines, name="item_lines"),
    path("customer-equipment/", customer_equipment, name="customer_equipment"),
    path(
        "customer-equipment-line/",
        customer_equipment_line,
        name="customer_equipment_line",
    ),
    path("prices/", prices, name="prices"),
    path("items-issued/", items_issued, name="items_issued"),
    path("issued-details/", issued_details, name="issued_details"),
    path("item-vendors/", item_vendors, name="item_vendors"),
    path("item-extras/", item_extras, name="item_extras"),
    path("vendor-lists/", vendor_lists, name="vendor_lists"),
    path("vendor-pils/", vendor_pils, name="vendor_pils"),
    path("dart-mo-spares/", dart_mo_spares, name="dart_mo_spares"),
]
