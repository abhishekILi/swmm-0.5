import { ColDef } from "ag-grid-community";

const TEXT_FILTER: Pick<ColDef, "filter" | "floatingFilter"> = { filter: "agTextColumnFilter", floatingFilter: true };

export const SURVEY_CART_COLUMNS: ColDef[] = [
  { field: "syncStatus", headerName: "ILMS Sync Status", width: 140, ...TEXT_FILTER },
  { field: "itemCode", headerName: "MO Item Code", flex: 1, ...TEXT_FILTER },
  { field: "hodApprovalStatus", headerName: "HOD Approval Status", width: 160, ...TEXT_FILTER },
  { field: "itemDescription", headerName: "Item Description", flex: 1.4, ...TEXT_FILTER },
  { field: "denomination", headerName: "Denomination", width: 130, ...TEXT_FILTER },
  { field: "qty", headerName: "Survey Qty", width: 110, ...TEXT_FILTER },
  { field: "category", headerName: "Category", width: 110, ...TEXT_FILTER },
  { field: "equipmentNomenclature", headerName: "Equipment Nomenclature", flex: 1, ...TEXT_FILTER },
  { field: "dartNo", headerName: "DART No", width: 120, ...TEXT_FILTER },
];

export const PTS_CART_COLUMNS: ColDef[] = [
  { field: "syncStatus", headerName: "ILMS Sync Status", width: 140, ...TEXT_FILTER },
  { field: "itemCode", headerName: "MO Item Code", flex: 1, ...TEXT_FILTER },
  { field: "itemDescription", headerName: "Item Name", flex: 1.4, ...TEXT_FILTER },
  { field: "denomination", headerName: "Denomination", width: 130, ...TEXT_FILTER },
  { field: "qty", headerName: "Demand Qty", width: 110, ...TEXT_FILTER },
  { field: "category", headerName: "Category", width: 110, ...TEXT_FILTER },
  { field: "dartNo", headerName: "Dart No", width: 120, ...TEXT_FILTER },
];

export const DEMAND_CART_COLUMNS: ColDef[] = [
  { field: "syncStatus", headerName: "ILMS Sync Status", width: 140, ...TEXT_FILTER },
  { field: "itemCode", headerName: "MO Item Code", flex: 1, ...TEXT_FILTER },
  { field: "itemDescription", headerName: "Item Name", flex: 1.2, ...TEXT_FILTER },
  { field: "ilmsDemandNo", headerName: "ILMS Demand No.", width: 150, ...TEXT_FILTER },
  { field: "surveyNo", headerName: "Survey No.", width: 120, ...TEXT_FILTER },
  { field: "qty", headerName: "Demand Qty", width: 110, ...TEXT_FILTER },
  { field: "category", headerName: "Category", width: 110, ...TEXT_FILTER },
  { field: "dartNo", headerName: "DART No", width: 120, ...TEXT_FILTER },
  { field: "moVettingRemarks", headerName: "MO Vetting Remarks", flex: 1, ...TEXT_FILTER },
];

export const RECEIVE_CART_COLUMNS: ColDef[] = [
  { field: "syncStatus", headerName: "ILMS Sync Status", width: 140, ...TEXT_FILTER },
  { field: "itemCode", headerName: "MO Item Code", flex: 1, ...TEXT_FILTER },
  { field: "moIssueStatus", headerName: "MO Item Issue Status", width: 170, ...TEXT_FILTER },
  { field: "itemDescription", headerName: "Item Description", flex: 1.2, ...TEXT_FILTER },
  { field: "denomination", headerName: "Denomination", width: 130, ...TEXT_FILTER },
  { field: "demandNo", headerName: "Demand No", width: 120, ...TEXT_FILTER },
  { field: "demandType", headerName: "Demand Type", width: 130, ...TEXT_FILTER },
  { field: "surveyNo", headerName: "Survey No.", width: 120, ...TEXT_FILTER },
  { field: "qty", headerName: "Demand Qty", width: 110, ...TEXT_FILTER },
  // BACKEND GAP: `qty_issued_by_mo` is hardcoded to "—" server-side (`ilms/views.py`
  // `_receive_row()`) — no model field tracks it yet, so this column is always blank for now.
  { field: "moIssueQty", headerName: "MO Issue Qty", width: 120, ...TEXT_FILTER },
  { field: "category", headerName: "CRP Category", width: 130, ...TEXT_FILTER },
  { field: "dartNo", headerName: "DART No", width: 120, ...TEXT_FILTER },
];

export const IIF_CART_COLUMNS: ColDef[] = [
  { field: "syncStatus", headerName: "ILMS Sync Status", width: 140, ...TEXT_FILTER },
  { field: "itemCode", headerName: "SWMM Pattern No", flex: 1, ...TEXT_FILTER },
  { field: "incattingStatus", headerName: "INcatting Status", width: 140, ...TEXT_FILTER },
  { field: "hodApprovalStatus", headerName: "HOD Approval Status", width: 160, ...TEXT_FILTER },
  { field: "itemDescription", headerName: "Item Description", flex: 1.2, ...TEXT_FILTER },
  { field: "equipmentClass", headerName: "Equipment Class", flex: 1, ...TEXT_FILTER },
  { field: "category", headerName: "Category", width: 110, ...TEXT_FILTER },
];

export const PTS_RIO_PENDING_CART_COLUMNS: ColDef[] = [
  { field: "syncStatus", headerName: "ILMS Sync Status", width: 140, ...TEXT_FILTER },
  { field: "itemCode", headerName: "MO Item Code", flex: 1, ...TEXT_FILTER },
  { field: "hodApprovalStatus", headerName: "HOD Approval Status", width: 160, ...TEXT_FILTER },
  { field: "demandType", headerName: "Demand Type", width: 130, ...TEXT_FILTER },
  { field: "itemDescription", headerName: "Item Description", flex: 1.2, ...TEXT_FILTER },
  { field: "denomination", headerName: "Denomination", width: 130, ...TEXT_FILTER },
  { field: "qty", headerName: "Survey Qty", width: 110, ...TEXT_FILTER },
  { field: "category", headerName: "Category", width: 110, ...TEXT_FILTER },
  { field: "equipmentNomenclature", headerName: "Equipment Nomenclature", flex: 1, ...TEXT_FILTER },
  { field: "dartNo", headerName: "DART No", width: 120, ...TEXT_FILTER },
  { field: "demandNo", headerName: "Demand No.", width: 130, ...TEXT_FILTER },
];
