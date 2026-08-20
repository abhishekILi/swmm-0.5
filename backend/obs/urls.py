from django.urls import path

from .views import (
    AuthorityViewSet,
    DemandViewSet,
    DenominationViewSet,
    EditMiscellaneousMasterDataView,
    EquipmentClassViewSet,
    IssueListViewSet,
    IssueViewSet,
    MiscellaneousMasterDataView,
    NotInCattedItemViewSet,
    PlannedRoutineSpareListViewSet,
    PostDemandViewSet,
    PostReceiveViewSet,
    PostSurveyViewSet,
    ReceiveViewSet,
    ReturnViewSet,
    RoutineSpareUsageViewSet,
    SpareClassViewSet,
    SparesMappingViewSet,
    SparesViewSet,
    SurveyViewSet,
)

app_name = "obs"

spares_list = SparesViewSet.as_view({"get": "list", "post": "create"})
spares_detail = SparesViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
spares_search = SparesViewSet.as_view({"get": "search"})
spares_low_stock = SparesViewSet.as_view({"get": "low_stock"})
spares_critical = SparesViewSet.as_view({"get": "critical"})
spares_d787j = SparesViewSet.as_view({"get": "d787j_deficiency"})
spares_dashboard = SparesViewSet.as_view({"get": "dashboard"})
spares_ship_dashboard = SparesViewSet.as_view({"get": "ship_dashboard"})
verify_pattern = SparesViewSet.as_view({"post": "verify_pattern"})
update_pattern = SparesViewSet.as_view({"post": "update_pattern"})
defect_requisition = SparesViewSet.as_view({"get": "defect_requisition"})
multi_issue = SparesViewSet.as_view({"post": "multi_issue"})
routine_multi_issue = SparesViewSet.as_view({"post": "routine_multi_issue"})
defect_multi_issue = SparesViewSet.as_view({"post": "defect_multi_issue"})
initiate_survey = SparesViewSet.as_view({"post": "initiate_survey_from_payload"})
initiate_demand = SparesViewSet.as_view({"post": "initiate_demand_from_payload"})
detail_summary = SparesViewSet.as_view({"get": "detail_summary"})
check_wed_mapping = SparesViewSet.as_view({"post": "check_wed_mapping"})
spares_import_excel = SparesViewSet.as_view({"post": "import_excel"})
spares_export_excel = SparesViewSet.as_view({"get": "export_excel"})
spares_download_template = SparesViewSet.as_view({"get": "download_template"})
spares_master_dropdown = SparesViewSet.as_view({"get": "master_dropdown"})
spares_defect_spares_for_dart = SparesViewSet.as_view({"get": "defect_spares_for_dart"})
spares_search_history = SparesViewSet.as_view({"get": "search_history"})
spares_add_from_ilms = SparesViewSet.as_view({"post": "add_from_ilms"})
spares_submit_validated_inventory = SparesViewSet.as_view(
    {"post": "submit_validated_inventory_data"}
)

spare_classes = SpareClassViewSet.as_view({"get": "list", "post": "create"})
spare_classes_by_department = SpareClassViewSet.as_view({"get": "by_department"})
equipment_classes = EquipmentClassViewSet.as_view({"get": "list", "post": "create"})
equipment_classes_by_spare = EquipmentClassViewSet.as_view({"get": "by_spare_class"})
denominations = DenominationViewSet.as_view({"get": "list", "post": "create"})
authorities = AuthorityViewSet.as_view({"get": "list", "post": "create"})

issues = IssueViewSet.as_view({"get": "list", "post": "create"})
issue_detail = IssueViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
issued_to_maintainers = IssueViewSet.as_view({"get": "issued_to_maintainers"})
ty_loan = IssueViewSet.as_view({"get": "ty_loan"})
issue_list = IssueListViewSet.as_view({"get": "list"})
returns = ReturnViewSet.as_view({"get": "list", "post": "create"})
return_detail = ReturnViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)
returned_spares = ReturnViewSet.as_view({"get": "returned_spares"})
commands = ReturnViewSet.as_view({"get": "commands"})
ships = ReturnViewSet.as_view({"get": "ships"})

surveys = SurveyViewSet.as_view({"get": "list", "post": "create"})
survey_detail = SurveyViewSet.as_view({"get": "retrieve"})
survey_complete = SurveyViewSet.as_view({"post": "complete"})
survey_import_excel = SurveyViewSet.as_view({"post": "import_excel"})
post_surveys = PostSurveyViewSet.as_view({"get": "list", "post": "create"})
pts_list_view = PostSurveyViewSet.as_view({"get": "pts_list"})
pts_detail_view = PostSurveyViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update"}
)
demands = DemandViewSet.as_view({"get": "list", "post": "create"})
demand_detail = DemandViewSet.as_view({"get": "retrieve"})
demand_complete = DemandViewSet.as_view({"post": "complete_from_payload"})
demand_detail_complete = DemandViewSet.as_view({"post": "complete"})
post_demands = PostDemandViewSet.as_view({"get": "list", "post": "create"})
receives = ReceiveViewSet.as_view({"get": "list", "post": "create"})
receive_detail = ReceiveViewSet.as_view({"get": "retrieve"})
receive_complete = ReceiveViewSet.as_view({"post": "complete"})
post_receives = PostReceiveViewSet.as_view({"get": "list", "post": "create"})

routine_usage = RoutineSpareUsageViewSet.as_view({"get": "list", "post": "create"})
routine_names = RoutineSpareUsageViewSet.as_view({"get": "routines"})
routine_descriptions = RoutineSpareUsageViewSet.as_view({"get": "routine_descriptions"})
planned_spares = PlannedRoutineSpareListViewSet.as_view(
    {"get": "list", "post": "create"}
)
planned_requisition = PlannedRoutineSpareListViewSet.as_view({"get": "requisition"})
delete_requisition = PlannedRoutineSpareListViewSet.as_view(
    {"post": "delete_requisition_spare"}
)
delete_defect_requisition = PlannedRoutineSpareListViewSet.as_view(
    {"post": "delete_defect_requisition_spare"}
)
soft_delete_cart = PlannedRoutineSpareListViewSet.as_view(
    {"post": "soft_delete_after_cart"}
)
soft_delete_cart_defect = PlannedRoutineSpareListViewSet.as_view(
    {"post": "soft_delete_after_cart_defect"}
)
not_in_catted_pending = NotInCattedItemViewSet.as_view({"get": "pending"})
not_in_catted_mark = NotInCattedItemViewSet.as_view({"post": "mark_incatted"})

spares_mapping_list = SparesMappingViewSet.as_view({"get": "list", "post": "create"})
spares_mapping_detail = SparesMappingViewSet.as_view(
    {
        "get": "retrieve",
        "put": "update",
        "patch": "partial_update",
        "delete": "destroy",
    }
)

urlpatterns = [
    path("", spares_dashboard, name="home"),
    path("survey/add/", post_surveys, name="survey_request"),
    path("demand/add/", post_demands, name="demand_request"),
    path("search_result/", spares_search, name="search_result"),
    path("search_new_result/", spares_search, name="search_new_result"),
    path("search_result_50/", spares_low_stock, name="search_result_less_than_fifty"),
    path("view/", spares_list, name="view"),
    path("view/<int:pk>/", spares_detail, name="view_pk"),
    path("view_fifty/", spares_low_stock, name="viewfifty"),
    path("view_fifty/<int:pk>/", spares_detail, name="viewfifty_pk"),
    path("add/", spares_list, name="add"),
    path("addSpare/<str:code>/", spares_add_from_ilms, name="addSpare"),
    path("addSpare/", spares_add_from_ilms, name="addSpare_pk"),
    path("miscellaneous/", MiscellaneousMasterDataView.as_view(), name="miscellaneous"),
    path(
        "edit_miscellaneous/",
        EditMiscellaneousMasterDataView.as_view(),
        name="edit_miscellaneous",
    ),
    path("edit/", spares_list, name="edit"),
    path("edit/<int:pk>/", spares_detail, name="edit_pk"),
    path("issue_list/", issue_list, name="issuelist"),
    path("issue/", issues, name="issue"),
    path("issue/<int:pk>/", issue_detail, name="issue_pk"),
    path("multi_spares/", spares_list, name="multi_spares"),
    path("multi_issue_spare/", multi_issue, name="multi_issue_spare"),
    path(
        "routine_multi_issue_spare/",
        routine_multi_issue,
        name="routine_multi_issue_spare",
    ),
    path(
        "defect_multi_issue_spare/", defect_multi_issue, name="defect_multi_issue_spare"
    ),
    path("return/", returns, name="return"),
    path("return/<int:pk>/", return_detail, name="return_pk"),
    path("survey_list/", surveys, name="surveylist"),
    path("surveys/<int:pk>/complete/", survey_complete, name="survey_complete"),
    path("survey_details/", surveys, name="surveydetails"),
    path("survey_details/<int:pk>/", survey_detail, name="surveydetails_pk"),
    path(
        "survey_details/<int:pk>/complete/",
        survey_complete,
        name="surveydetails_complete",
    ),
    path("pts_list/", pts_list_view, name="ptslist"),
    path("pts/", pts_list_view, name="ptsdetails"),
    path("pts/<int:pk>/", pts_detail_view, name="ptsdetails_pk"),
    path("demand_list/", demands, name="demandlist"),
    path("demand_details/", demands, name="demanddetails"),
    path("demand_details/<int:pk>/", demand_detail, name="demanddetails_pk"),
    path(
        "demand_details/<int:pk>/complete/",
        demand_detail_complete,
        name="demanddetails_complete",
    ),
    path("demandgenerate/", demand_complete, name="demandgenerate"),
    path("receive_list/", receives, name="receivelist"),
    path("receive_details/", receives, name="receivedetails"),
    path("receive_details/<int:pk>/", receive_detail, name="receivedetails_pk"),
    path(
        "receive_details/<int:pk>/complete/",
        receive_complete,
        name="receivedetails_complete",
    ),
    path(
        "history_search/<int:activate_btn>/",
        spares_search_history,
        name="history_activate",
    ),
    path("history_search/", spares_search_history, name="history_search"),
    path("get_spare_detail/<int:pk>/", detail_summary, name="get_spare_detail"),
    path("spare_class/", spare_classes, name="spare_class"),
    path(
        "spare_class/<int:department_id>/",
        spare_classes_by_department,
        name="spare_class_pk",
    ),
    path("equipment_class/", equipment_classes, name="equipment_class"),
    path(
        "equipment_class/<int:department_id>/<int:spare_class_id>/",
        equipment_classes_by_spare,
        name="equipment_class_pk",
    ),
    path("master/", spares_master_dropdown, name="master"),
    path("authorities/", authorities, name="authorities"),
    path("denominations/", denominations, name="denominations"),
    path("spares-mapping/", spares_mapping_list, name="spares_mapping"),
    path(
        "spares-mapping/<int:pk>/",
        spares_mapping_detail,
        name="spares_mapping_detail",
    ),
    path("import/", spares_import_excel, name="import_excel_file"),
    path("export-excel/", spares_export_excel, name="export_excel_file"),
    path(
        "download-template/",
        spares_download_template,
        name="download_excel_template",
    ),
    path("import_survey_action/", survey_import_excel, name="import_survey_file"),
    path("about/", spares_dashboard, name="about_us"),
    path("spare_info/", spares_dashboard, name="spare_info"),
    path("thumbnail/", spares_dashboard, name="thumbnail"),
    path(
        "get-routine-descriptions/",
        routine_descriptions,
        name="get_routine_descriptions",
    ),
    path("get-routing-names/", routine_names, name="get_routing_names"),
    path("get-planed-routing-names/", routine_names, name="get_Planned_routing_names"),
    path(
        "get-planed-routing-description/",
        routine_descriptions,
        name="get_Planned_routine_descriptions",
    ),
    path("generate-pdf-report/", spares_dashboard, name="generate-pdf-report"),
    path("total_obs_view/", spares_dashboard, name="total_obs_view"),
    path("requisition_list/<int:pk>/", planned_requisition, name="requisitionlist"),
    path(
        "defect_requisition_list/<int:pk>/",
        defect_requisition,
        name="defectrequisitionlist",
    ),
    path("requisition_details/", planned_requisition, name="requisition_details"),
    path(
        "defect_requisition_details/",
        defect_requisition,
        name="defect_requisition_details",
    ),
    path("routine_spares/<int:pk>/", routine_usage, name="routinespares"),
    path("routine_spares", routine_usage, name="routinespares"),
    path(
        "defect_spares/<int:pk>/",
        spares_defect_spares_for_dart,
        name="defectspares",
    ),
    path("defect_spares", spares_defect_spares_for_dart, name="defectspares"),
    path("iif_list/", not_in_catted_pending, name="iiflist"),
    path("iifdetails/<int:pk>/", not_in_catted_mark, name="iif_details"),
    path("custom_user_profile/", spares_dashboard, name="custom_user_profile"),
    path("import-excel-file/", spares_import_excel, name="import_excel_file"),
    path(
        "submit-validated-inventory-data/",
        spares_submit_validated_inventory,
        name="submit_validated_inventory_data",
    ),
    path("dashboardshore/", spares_ship_dashboard, name="dashboardshore"),
    path("check-wed-mapping/", check_wed_mapping, name="check_wed_mapping"),
    path(
        "sparesissued_tomaintainers/",
        issued_to_maintainers,
        name="sparesissued_tomaintainers",
    ),
    path("sparesissued_ontyloan/", ty_loan, name="sparesissued_ontyloan"),
    path("sparesreturned/", returned_spares, name="sparesreturned"),
    path(
        "spares_lessthen50per_in_inventory/",
        spares_low_stock,
        name="spares_lessthen50per_in_inventory",
    ),
    path("d787jdefficiency/", spares_d787j, name="d787jdefficiency"),
    path("criticalsparelist/", spares_critical, name="criticalsparelist"),
    path("verify-pattern/", verify_pattern, name="verify_pattern_number"),
    path("update-spare-pattern/", update_pattern, name="update_spare_pattern"),
    path("initiate_obs_survey/", initiate_survey, name="initiate_obs_survey"),
    path("initiate_obs_demand/", initiate_demand, name="initiate_obs_demand"),
    path("wediifdetails/<int:pk>/", not_in_catted_mark, name="wediif_details"),
    path("get_commands/", commands, name="get_commands"),
    path("get_ships_by_command/", ships, name="get_ships_by_command"),
    path(
        "delete-requisition-spare/", delete_requisition, name="delete_requisition_spare"
    ),
    path(
        "delete-defect-requisition-spare/",
        delete_defect_requisition,
        name="delete_defect_requisition_spare",
    ),
    path("soft-delete-after-cart/", soft_delete_cart, name="soft_delete_after_cart"),
    path(
        "soft-delete-after-cart-defect/",
        soft_delete_cart_defect,
        name="soft_delete_after_cart_defect",
    ),
]
