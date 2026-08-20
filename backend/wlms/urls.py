from django.urls import path

from . import views

app_name = "WLMS"

dashboard = views.WLMSSpareViewSet.as_view({"get": "dashboard"})
spares = views.WLMSSpareViewSet.as_view({"get": "list", "post": "create"})
spare_search = views.WLMSSpareViewSet.as_view({"get": "list"})
equipment_list = views.WLMSSpareViewSet.as_view({"get": "equipment_list"})
spares_by_equipment = views.WLMSSpareViewSet.as_view({"get": "by_equipment"})
spare_context = views.WLMSSpareViewSet.as_view({"get": "context_from_query"})
spare_routine_context = views.WLMSSpareViewSet.as_view({"get": "routine_context"})
spare_equipment_for_spares = views.WLMSSpareViewSet.as_view(
    {"get": "equipment_for_spares"}
)

equipment = views.WLMSEquipmentViewSet.as_view({"get": "list", "post": "create"})
insma_equipment = views.WLMSEquipmentViewSet.as_view({"get": "insma_equipment"})
unmapped_equipment = views.WLMSEquipmentViewSet.as_view({"get": "unmapped"})
sfd_equipment_for_wed = views.SpareDataMapViewSet.as_view(
    {"get": "sfd_equipment_for_wed"}
)
obs_spare_class = views.SpareDataMapViewSet.as_view({"get": "obs_spare_class"})
spare_data_map = views.SpareDataMapViewSet.as_view({"get": "list", "post": "create"})
planned_descriptions = views.PlannedSparesDescriptionViewSet.as_view(
    {"get": "list", "post": "create"}
)
planned_spares_by_routine = views.PlannedWEDSpareListViewSet.as_view(
    {"get": "by_routine"}
)
check_routine_mapping = views.PlannedWEDSpareListViewSet.as_view(
    {"get": "check_routine_mapping"}
)

surveys = views.SurveyReceiptsDetailsViewSet.as_view({"get": "list", "post": "create"})
survey_inbox = views.SurveyReceiptsDetailsViewSet.as_view({"get": "inbox"})
survey_outbox = views.SurveyReceiptsDetailsViewSet.as_view({"get": "outbox"})
survey_add_to_cart = views.SurveyReceiptsDetailsViewSet.as_view({"post": "add_to_cart"})
survey_send_for_approval = views.SurveyReceiptsDetailsViewSet.as_view(
    {"post": "send_for_approval"}
)
survey_bulk_send = views.SurveyReceiptsDetailsViewSet.as_view(
    {"post": "bulk_send_for_approval"}
)
survey_approve = views.SurveyReceiptsDetailsViewSet.as_view({"post": "approve"})
survey_bulk_approve = views.SurveyReceiptsDetailsViewSet.as_view(
    {"post": "bulk_approve"}
)
survey_mark_synced = views.SurveyReceiptsDetailsViewSet.as_view({"post": "mark_synced"})
survey_pending_list = views.SurveyReceiptsDetailsViewSet.as_view(
    {"get": "pending_list"}
)
survey_forms = views.SurveyFormsDetailsViewSet.as_view(
    {"get": "list", "post": "create"}
)
survey_edps_pdf = views.SurveyReceiptsDetailsViewSet.as_view({"get": "edps_pdf"})
survey_forms_generate_number = views.SurveyFormsDetailsViewSet.as_view(
    {"post": "generate_number"}
)
survey_items = views.SurveyFormsItemsViewSet.as_view({"get": "list", "post": "create"})

pts = views.PTSDemandDetailsViewSet.as_view({"get": "list", "post": "create"})
pts_add_to_cart = views.PTSDemandDetailsViewSet.as_view({"post": "add_to_cart"})
pts_send_for_approval = views.PTSDemandDetailsViewSet.as_view(
    {"post": "send_for_approval"}
)
pts_bulk_send = views.PTSDemandDetailsViewSet.as_view(
    {"post": "bulk_send_for_approval"}
)
pts_approve = views.PTSDemandDetailsViewSet.as_view({"post": "approve"})
pts_bulk_approve = views.PTSDemandDetailsViewSet.as_view({"post": "bulk_approve"})
pts_mark_synced = views.PTSDemandDetailsViewSet.as_view({"post": "mark_synced"})
pts_pending_list = views.PTSDemandDetailsViewSet.as_view({"get": "pending_list"})
pts_generate_number = views.PTSDemandDetailsViewSet.as_view({"post": "generate_number"})
pts_items = views.PTSItemsViewSet.as_view({"get": "list", "post": "create"})

demands = views.DemandDetailsViewSet.as_view({"get": "list", "post": "create"})
demand_add_to_cart = views.DemandDetailsViewSet.as_view({"post": "add_to_cart"})
demand_send_for_approval = views.DemandDetailsViewSet.as_view(
    {"post": "send_for_approval"}
)
demand_bulk_send = views.DemandDetailsViewSet.as_view(
    {"post": "bulk_send_for_approval"}
)
demand_approve = views.DemandDetailsViewSet.as_view({"post": "approve"})
demand_bulk_approve = views.DemandDetailsViewSet.as_view({"post": "bulk_approve"})
demand_mark_synced = views.DemandDetailsViewSet.as_view({"post": "mark_synced"})
demand_pending_list = views.DemandDetailsViewSet.as_view({"get": "pending_list"})
demand_generate_number = views.DemandDetailsViewSet.as_view({"post": "generate_number"})
demand_receive_queue = views.DemandDetailsViewSet.as_view({"get": "receive_queue"})
demand_consolidation = views.DemandDetailsViewSet.as_view({"get": "consolidation"})
receives = views.ReceiveDemandDetailsViewSet.as_view({"get": "list", "post": "create"})

iif = views.WEDIIFViewSet.as_view({"get": "list", "post": "create"})
iif_add_items = views.WEDIIFViewSet.as_view({"post": "add_items"})
iif_send_for_approval = views.WEDIIFViewSet.as_view({"post": "send_for_approval"})
iif_approve = views.WEDIIFViewSet.as_view({"post": "approve"})
iif_inbox = views.WEDIIFViewSet.as_view({"get": "inbox"})
iif_outbox = views.WEDIIFViewSet.as_view({"get": "outbox"})
iif_mark_synced = views.WEDIIFViewSet.as_view({"post": "mark_synced"})
iif_details = views.WEDIIFDetailsViewSet.as_view(
    {"get": "retrieve", "post": "update", "put": "update", "patch": "partial_update"}
)

dart_wed_spares = views.DartWedSpareViewSet.as_view({"get": "list", "post": "create"})
dart_wed_spare_detail = views.DartWedSpareViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

signal_demands = views.SignalDemandViewSet.as_view({"get": "list", "post": "create"})
signal_demand_forward = views.SignalDemandViewSet.as_view({"post": "forward"})
signal_demand_approve = views.SignalDemandViewSet.as_view({"post": "approve"})
signal_demand_reject = views.SignalDemandViewSet.as_view({"post": "reject"})
signal_demand_cancel = views.SignalDemandViewSet.as_view({"post": "cancel"})

urlpatterns = [
    path("dashboardwlms/", dashboard, name="dashboardwlms"),
    path("raise_replenishmentdemand/", demands, name="raise_replenishmentdemand"),
    path("surveyptswlms/", pts, name="surveyptswlms"),
    path("surveynormalwlms/", surveys, name="surveynormalwlms"),
    path("surveytyloanwlms/", surveys, name="surveytyloanwlms"),
    path("specialdemand/", demands, name="specialdemand"),
    path("signaldemand/", signal_demands, name="signaldemand"),
    path("raisepts/", pts, name="raisepts"),
    path("raisetyloan/", surveys, name="raisetyloan"),
    path("itemsearchwlms/", spare_search, name="itemsearchwlms"),
    path("itemsearchwlms/ajax/", spare_search, name="itemsearchwlms_ajax"),
    path(
        "itemsearchwlms/equipments/", equipment_list, name="itemsearchwlms_equipments"
    ),
    path("itemsearchwlms/spares/", spares_by_equipment, name="itemsearchwlms_spares"),
    path("wlmssurveylist/", survey_pending_list, name="wlmssurveylist"),
    path("wlmsdemandlist/", demand_pending_list, name="wlmsdemandlist"),
    path("wlmsreceivelist/", receives, name="wlmsreceivelist"),
    path("wlmsptslist/", pts_pending_list, name="wlmsptslist"),
    path("wlmsforapproval/", survey_inbox, name="wlmsforapproval"),
    path("wlmsinbox/", survey_inbox, name="wlmsinbox"),
    path("wlmsoutbox/", views.wlms_combined_outbox, name="wlmsoutbox"),
    path("send-common-api/", views.send_wed_common_api, name="send-common-api"),
    path(
        "sync-equipment-from-wed/",
        views.sync_equipment_from_wed,
        name="sync_equipment_from_wed",
    ),
    path(
        "sync-spares-from-wed/",
        views.sync_spares_from_wed,
        name="sync_spares_from_wed",
    ),
    path("wlmsmaster/", spare_data_map, name="wlms_master"),
    path("wlmsptsdetails/", pts, name="wlmsptsdetails"),
    path("wlmsdemanddetails/", demands, name="wlmsdemanddetails"),
    path("wlmsreceivedetails/", receives, name="wlmsreceivedetails"),
    path("wlmssurveydetails/", surveys, name="wlmssurveydetails"),
    path("ssdemand/", demands, name="ssdemand"),
    path("riodemand/", demands, name="riodemand"),
    path("item-search-detail/", spare_context, name="itemsearchwlms_detail"),
    path("wlmsiif/", iif, name="wlmsiif"),
    path("ptsraised_surveypending/", pts, name="ptsraised_surveypending"),
    path("api/insma-equipment/", insma_equipment, name="get_insma_equipment"),
    path("api/obs-spare-class/", obs_spare_class, name="get_obs_spare_class"),
    path("api/wed-equipment/", unmapped_equipment, name="get_wed_equipment"),
    path("wlmsiifhistory/", iif, name="wlmsiifhistory"),
    path(
        "check_and_redirect_routine/",
        check_routine_mapping,
        name="check_and_redirect_routine",
    ),
    path("wlmsiifdetails/<int:pk>/", iif_details, name="wlmsiifdetails"),
    path("survey/edps-pdf/", survey_edps_pdf, name="wlms_edps_pdf"),
    path("wlmshistory/", spares, name="wlmshistory"),
    path(
        "get_wed_spare_equipment/",
        spare_equipment_for_spares,
        name="get_wed_spare_equipment",
    ),
    path(
        "survey_send_hod_approval/", survey_bulk_send, name="survey_send_hod_approval"
    ),
    path(
        "demand_send_hod_approval/", demand_bulk_send, name="demand_send_hod_approval"
    ),
    path("pts_send_hod_approval/", pts_bulk_send, name="pts_send_hod_approval"),
    path("hod-approve/", pts_bulk_approve, name="hod-approve"),
    path("add-to-iif-cart/", iif_add_items, name="add_to_iif_cart"),
    path("save_receipt_details/", receives, name="save_receipt_details"),
    path(
        "get-sfd-equipment-for-wed/",
        sfd_equipment_for_wed,
        name="get_sfd_equipment_for_wed",
    ),
    path("wlms-send-hod-approval/", demand_bulk_send, name="wlmssendhodapproval"),
    # Approval-workflow actions that already existed in views.py but were never
    # routed for Survey/PTS/Demand (only bulk-send was wired previously).
    path("survey/add-to-cart/", survey_add_to_cart, name="survey_add_to_cart"),
    path(
        "survey/<int:pk>/send-for-approval/",
        survey_send_for_approval,
        name="survey_send_for_approval",
    ),
    path("survey/<int:pk>/approve/", survey_approve, name="survey_approve"),
    path("survey/bulk-approve/", survey_bulk_approve, name="survey_bulk_approve"),
    path(
        "survey/<int:pk>/mark-synced/",
        survey_mark_synced,
        name="survey_mark_synced",
    ),
    path(
        "survey-forms/<int:pk>/generate-number/",
        survey_forms_generate_number,
        name="survey_forms_generate_number",
    ),
    path("survey-items/", survey_items, name="survey_items"),
    path("pts/add-to-cart/", pts_add_to_cart, name="pts_add_to_cart"),
    path(
        "pts/<int:pk>/send-for-approval/",
        pts_send_for_approval,
        name="pts_send_for_approval",
    ),
    path("pts/<int:pk>/approve/", pts_approve, name="pts_approve"),
    path("pts/<int:pk>/mark-synced/", pts_mark_synced, name="pts_mark_synced"),
    path(
        "pts/<int:pk>/generate-number/",
        pts_generate_number,
        name="pts_generate_number",
    ),
    path("pts-items/", pts_items, name="pts_items"),
    path("demand/add-to-cart/", demand_add_to_cart, name="demand_add_to_cart"),
    path(
        "demand/<int:pk>/send-for-approval/",
        demand_send_for_approval,
        name="demand_send_for_approval",
    ),
    path("demand/<int:pk>/approve/", demand_approve, name="demand_approve"),
    path("demand/bulk-approve/", demand_bulk_approve, name="demand_bulk_approve"),
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
    path("demand/receive-queue/", demand_receive_queue, name="demand_receive_queue"),
    path("demand/consolidation/", demand_consolidation, name="demand_consolidation"),
    path(
        "spares/<int:pk>/routine-context/",
        spare_routine_context,
        name="spare_routine_context",
    ),
    path(
        "wlmsiif/<int:pk>/send-for-approval/",
        iif_send_for_approval,
        name="iif_send_for_approval",
    ),
    path("wlmsiif/<int:pk>/approve/", iif_approve, name="iif_approve"),
    path("wlmsiif/inbox/", iif_inbox, name="iif_inbox"),
    path("wlmsiif/outbox/", iif_outbox, name="iif_outbox"),
    path("wlmsiif/<int:pk>/mark-synced/", iif_mark_synced, name="iif_mark_synced"),
    path("dart-wed-spares/", dart_wed_spares, name="dart_wed_spares"),
    path(
        "dart-wed-spares/<int:pk>/",
        dart_wed_spare_detail,
        name="dart_wed_spares_detail",
    ),
    path(
        "signaldemand/<int:pk>/forward/",
        signal_demand_forward,
        name="signal_demand_forward",
    ),
    path(
        "signaldemand/<int:pk>/approve/",
        signal_demand_approve,
        name="signal_demand_approve",
    ),
    path(
        "signaldemand/<int:pk>/reject/",
        signal_demand_reject,
        name="signal_demand_reject",
    ),
    path(
        "signaldemand/<int:pk>/cancel/",
        signal_demand_cancel,
        name="signal_demand_cancel",
    ),
]
